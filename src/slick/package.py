from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type

from .util.lang import classproperty, memoized
from .directives import PackageMeta


FLAG_HANDLER_RETURN_TYPE = Tuple[
    Optional[Iterable[str]], Optional[Iterable[str]], Optional[Iterable[str]]
]
FLAG_HANDLER_TYPE = Callable[[str, Iterable[str]], FLAG_HANDLER_RETURN_TYPE]

"""Allowed URL schemes for spack packages."""
_ALLOWED_URL_SCHEMES = ["http", "https", "ftp", "file", "git"]

class PackageBase(metaclass=PackageMeta):
    """This is the superclass for all Slick packages.

    ***The Package class***

    At its core, a package is a DSL specifying its
    requirements for build and run environment and its
    naming conventions - like where to download it and
    what variants it provides.

    Packages are written in pure Python (which is a metaclass DSL).

    There are two main parts of a Slick package:

      1. **The package class**.  Classes contain ``directives``, which are
         special functions, that add metadata (versions, patches,
         dependencies, and other information) to packages (see
         ``directives.py``). Directives provide the constraints that are
         used as input to the concretizer.

      2. **Package instances**. Once instantiated, a package is
         a ``concrete spec'' -- providing a specific instance of the package's
         options that is compatible with the package's requirementsa
         and the user's requested spec.

         Users may query this spec to build and run the package
         appropriately.

    **Package DSL**

    Look in ``lib/spack/docs`` or check https://spack.readthedocs.io for
    the full documentation of the package domain-specific language.  That
    used to be partially documented here, but as it grew, the docs here
    became increasingly out of date.
    """

    #
    # These are default values for instance variables.
    #

    #: By default, packages are not virtual
    #: Virtual packages override this attribute
    virtual = False

    #: Most Spack packages are used to install source or binary code while
    #: those that do not can be used to install a set of other Spack packages.
    has_code = True

    #: By default we build in parallel.  Subclasses can override this.
    parallel = True

    #: By default do not run tests within package's install()
    run_tests = False

    # FIXME: this is a bad object-oriented design, should be moved to Clang.
    #: By default do not setup mockup XCode on macOS with Clang
    use_xcode = False

    #: Keep -Werror flags, matches config:flags:keep_werror to override config
    # NOTE: should be type Optional[Literal['all', 'specific', 'none']] in 3.8+
    keep_werror: Optional[str] = None

    #: Most packages are NOT extendable. Set to True if you want extensions.
    extendable = False

    #: When True, add RPATHs for the entire DAG. When False, add RPATHs only
    #: for immediate dependencies.
    transitive_rpaths = True

    #: List of shared objects that should be replaced with a different library at
    #: runtime. Typically includes stub libraries like libcuda.so. When linking
    #: against a library listed here, the dependent will only record its soname
    #: or filename, not its absolute path, so that the dynamic linker will search
    #: for it. Note: accepts both file names and directory names, for example
    #: ``["libcuda.so", "stubs"]`` will ensure libcuda.so and all libraries in the
    #: stubs directory are not bound by path."""
    non_bindable_shared_objects: List[str] = []

    #: List of prefix-relative file paths (or a single path). If these do
    #: not exist after install, or if they exist but are not files,
    #: sanity checks fail.
    sanity_check_is_file: List[str] = []

    #: List of prefix-relative directory paths (or a single path). If
    #: these do not exist after install, or if they exist but are not
    #: directories, sanity checks will fail.
    sanity_check_is_dir: List[str] = []

    #: Boolean. Set to ``True`` for packages that require a manual download.
    #: This is currently used by package sanity tests and generation of a
    #: more meaningful fetch failure error.
    manual_download = False

    #: Set of additional options used when fetching package versions.
    fetch_options: Dict[str, Any] = {}

    #
    # Set default licensing information
    #
    #: Boolean. If set to ``True``, this software requires a license.
    #: If set to ``False``, all of the ``license_*`` attributes will
    #: be ignored. Defaults to ``False``.
    license_required = False

    #: String. Contains the symbol used by the license manager to denote
    #: a comment. Defaults to ``#``.
    license_comment = "#"

    #: List of strings. These are files that the software searches for when
    #: looking for a license. All file paths must be relative to the
    #: installation directory. More complex packages like Intel may require
    #: multiple licenses for individual components. Defaults to the empty list.
    license_files: List[str] = []

    #: List of strings. Environment variables that can be set to tell the
    #: software where to look for a license if it is not in the usual location.
    #: Defaults to the empty list.
    license_vars: List[str] = []

    #: String. A URL pointing to license setup instructions for the software.
    #: Defaults to the empty string.
    license_url = ""

    #: Verbosity level, preserved across installs.
    _verbose = None

    #: index of patches by sha256 sum, built lazily
    _patches_by_hash = None

    #: Package homepage where users can find more information about the package
    homepage: Optional[str] = None

    #: Default list URL (place to find available versions)
    list_url: Optional[str] = None

    #: Link depth to which list_url should be searched for new versions
    list_depth = 0

    #: List of strings which contains GitHub usernames of package maintainers.
    #: Do not include @ here in order not to unnecessarily ping the users.
    maintainers: List[str] = []

    #: List of attributes to be excluded from a package's hash.
    metadata_attrs = [
        "homepage",
        "url",
        "urls",
        "list_url",
        "extendable",
        "parallel",
        "make_jobs",
        "maintainers",
        "tags",
    ]

    #: Boolean. If set to ``True``, the smoke/install test requires a compiler.
    #: This is currently used by smoke tests to ensure a compiler is available
    #: to build a custom test code.
    test_requires_compiler = False

    #: List of test failures encountered during a smoke/install test run.
    test_failures = None

    #: TestSuite instance used to manage smoke/install tests for one or more specs.
    test_suite = None

    #: Path to the log file used for tests
    test_log_file = None

    def __init__(self, spec):
        # this determines how the package should be built.
        self.spec = spec

        # Allow custom staging paths for packages
        self.path = None

        # Keep track of whether or not this package was installed from
        # a binary cache.
        self.installed_from_binary_cache = False

        # Ensure that only one of these two attributes are present
        if getattr(self, "url", None) and getattr(self, "urls", None):
            msg = "a package can have either a 'url' or a 'urls' attribute"
            msg += " [package '{0.name}' defines both]"
            raise ValueError(msg.format(self))

        self._fetcher = None

        # Set up timing variables
        self._fetch_time = 0.0

        self.win_rpath = fsys.WindowsSimulatedRPath(self)

        if self.is_extension:
            pkg_cls = spack.repo.path.get_pkg_class(self.extendee_spec.name)
            pkg_cls(self.extendee_spec)._check_extendable()

        super(PackageBase, self).__init__()

    @classmethod
    def possible_dependencies(
        cls,
        transitive=True,
        expand_virtuals=True,
        deptype="all",
        visited=None,
        missing=None,
        virtuals=None,
    ):
        """Return dict of possible dependencies of this package.

        Args:
            transitive (bool or None): return all transitive dependencies if
                True, only direct dependencies if False (default True)..
            expand_virtuals (bool or None): expand virtual dependencies into
                all possible implementations (default True)
            deptype (str or tuple or None): dependency types to consider
            visited (dict or None): dict of names of dependencies visited so
                far, mapped to their immediate dependencies' names.
            missing (dict or None): dict to populate with packages and their
                *missing* dependencies.
            virtuals (set): if provided, populate with virtuals seen so far.

        Returns:
            (dict): dictionary mapping dependency names to *their*
                immediate dependencies

        Each item in the returned dictionary maps a (potentially
        transitive) dependency of this package to its possible
        *immediate* dependencies. If ``expand_virtuals`` is ``False``,
        virtual package names wil be inserted as keys mapped to empty
        sets of dependencies.  Virtuals, if not expanded, are treated as
        though they have no immediate dependencies.

        Missing dependencies by default are ignored, but if a
        missing dict is provided, it will be populated with package names
        mapped to any dependencies they have that are in no
        repositories. This is only populated if transitive is True.

        Note: the returned dict *includes* the package itself.

        """
        deptype = spack.dependency.canonical_deptype(deptype)

        visited = {} if visited is None else visited
        missing = {} if missing is None else missing

        visited.setdefault(cls.name, set())

        for name, conditions in cls.dependencies.items():
            # check whether this dependency could be of the type asked for
            types = [dep.type for cond, dep in conditions.items()]
            types = set.union(*types)
            if not any(d in types for d in deptype):
                continue

            # expand virtuals if enabled, otherwise just stop at virtuals
            if spack.repo.path.is_virtual(name):
                if virtuals is not None:
                    virtuals.add(name)
                if expand_virtuals:
                    providers = spack.repo.path.providers_for(name)
                    dep_names = [spec.name for spec in providers]
                else:
                    visited.setdefault(cls.name, set()).add(name)
                    visited.setdefault(name, set())
                    continue
            else:
                dep_names = [name]

            # add the dependency names to the visited dict
            visited.setdefault(cls.name, set()).update(set(dep_names))

            # recursively traverse dependencies
            for dep_name in dep_names:
                if dep_name in visited:
                    continue

                visited.setdefault(dep_name, set())

                # skip the rest if not transitive
                if not transitive:
                    continue

                try:
                    dep_cls = spack.repo.path.get_pkg_class(dep_name)
                except spack.repo.UnknownPackageError:
                    # log unknown packages
                    missing.setdefault(cls.name, set()).add(dep_name)
                    continue

                dep_cls.possible_dependencies(
                    transitive, expand_virtuals, deptype, visited, missing, virtuals
                )

        return visited

    @classproperty
    def fullname(cls):
        """Name of this package, including the namespace"""
        return "%s.%s" % (cls.namespace, cls.name)

    @classproperty
    def fullnames(cls):
        """Fullnames for this package and any packages from which it inherits."""
        fullnames = []
        for cls in inspect.getmro(cls):
            namespace = getattr(cls, "namespace", None)
            if namespace:
                fullnames.append("%s.%s" % (namespace, cls.name))
            if namespace == "builtin":
                # builtin packages cannot inherit from other repos
                break
        return fullnames

    @classproperty
    def name(cls):
        """The name of this package.

        The name of a package is the name of its Python module, without
        the containing module names.
        """
        if cls._name is None:
            cls._name = cls.__name__
            if "." in cls._name:
                cls._name = cls._name[cls._name.rindex(".") + 1 :]
        return cls._name

    @classproperty
    def global_license_dir(cls):
        """Returns the directory where license files for all packages are stored."""
        return spack.util.path.canonicalize_path(spack.config.get("config:license_dir"))

    @property
    def global_license_file(self):
        """Returns the path where a global license file for this
        particular package should be stored."""
        if not self.license_files:
            return
        return os.path.join(
            self.global_license_dir, self.name, os.path.basename(self.license_files[0])
        )

    @property
    def version(self):
        if not self.spec.versions.concrete:
            raise ValueError(
                "Version requested for a package that" " does not have a concrete version."
            )
        return self.spec.versions[0]

    @classmethod
    @memoized
    def version_urls(cls):
        """OrderedDict of explicitly defined URLs for versions of this package.

        Return:
           An OrderedDict (version -> URL) different versions of this
           package, sorted by version.

        A version's URL only appears in the result if it has an an
        explicitly defined ``url`` argument. So, this list may be empty
        if a package only defines ``url`` at the top level.
        """
        version_urls = collections.OrderedDict()
        for v, args in sorted(cls.versions.items()):
            if "url" in args:
                version_urls[v] = args["url"]
        return version_urls

    def nearest_url(self, version):
        """Finds the URL with the "closest" version to ``version``.

        This uses the following precedence order:

          1. Find the next lowest or equal version with a URL.
          2. If no lower URL, return the next *higher* URL.
          3. If no higher URL, return None.

        """
        version_urls = self.version_urls()

        if version in version_urls:
            return version_urls[version]

        last_url = None
        for v, u in self.version_urls().items():
            if v > version:
                if last_url:
                    return last_url
            last_url = u

        return last_url

    def url_for_version(self, version):
        """Returns a URL from which the specified version of this package
        may be downloaded.

        version: class Version
            The version for which a URL is sought.

        See Class Version (version.py)
        """
        return self._implement_all_urls_for_version(version)[0]

    def update_external_dependencies(self, extendee_spec=None):
        """
        Method to override in package classes to handle external dependencies
        """
        pass

    def all_urls_for_version(self, version):
        """Return all URLs derived from version_urls(), url, urls, and
        list_url (if it contains a version) in a package in that order.

        Args:
            version (spack.version.Version): the version for which a URL is sought
        """
        uf = None
        if type(self).url_for_version != PackageBase.url_for_version:
            uf = self.url_for_version
        return self._implement_all_urls_for_version(version, uf)

    def _implement_all_urls_for_version(self, version, custom_url_for_version=None):
        if not isinstance(version, VersionBase):
            version = Version(version)

        urls = []

        # If we have a specific URL for this version, don't extrapolate.
        version_urls = self.version_urls()
        if version in version_urls:
            urls.append(version_urls[version])

        # if there is a custom url_for_version, use it
        if custom_url_for_version is not None:
            u = custom_url_for_version(version)
            if u not in urls and u is not None:
                urls.append(u)

        def sub_and_add(u):
            if u is None:
                return
            # skip the url if there is no version to replace
            try:
                spack.url.parse_version(u)
            except spack.url.UndetectableVersionError:
                return
            nu = spack.url.substitute_version(u, self.url_version(version))

            urls.append(nu)

        # If no specific URL, use the default, class-level URL
        sub_and_add(getattr(self, "url", None))
        for u in getattr(self, "urls", []):
            sub_and_add(u)

        sub_and_add(getattr(self, "list_url", None))

        # if no version-bearing URLs can be found, try them raw
        if not urls:
            default_url = getattr(self, "url", getattr(self, "urls", [None])[0])

            # if no exact match AND no class-level default, use the nearest URL
            if not default_url:
                default_url = self.nearest_url(version)

                # if there are NO URLs to go by, then we can't do anything
                if not default_url:
                    raise NoURLError(self.__class__)
            urls.append(spack.url.substitute_version(default_url, self.url_version(version)))

        return urls

    def find_valid_url_for_version(self, version):
        """Returns a URL from which the specified version of this package
        may be downloaded after testing whether the url is valid. Will try
        url, urls, and list_url before failing.

        version: class Version
            The version for which a URL is sought.

        See Class Version (version.py)
        """
        urls = self.all_urls_for_version(version)

        for u in urls:
            if spack.util.web.url_exists(u):
                return u

        return None

    @classmethod
    def dependencies_of_type(cls, *deptypes):
        """Get dependencies that can possibly have these deptypes.

        This analyzes the package and determines which dependencies *can*
        be a certain kind of dependency. Note that they may not *always*
        be this kind of dependency, since dependencies can be optional,
        so something may be a build dependency in one configuration and a
        run dependency in another.
        """
        return dict(
            (name, conds)
            for name, conds in cls.dependencies.items()
            if any(dt in cls.dependencies[name][cond].type for cond in conds for dt in deptypes)
        )

    @property
    def extendee_spec(self):
        """
        Spec of the extendee of this package, or None if it is not an extension
        """
        if not self.extendees:
            return None

        deps = []

        # If the extendee is in the spec's deps already, return that.
        for dep in self.spec.traverse(deptype=("link", "run")):
            if dep.name in self.extendees:
                deps.append(dep)

        # TODO: allow more than one active extendee.
        if deps:
            assert len(deps) == 1
            return deps[0]

        # if the spec is concrete already, then it extends something
        # that is an *optional* dependency, and the dep isn't there.
        if self.spec._concrete:
            return None
        else:
            # TODO: do something sane here with more than one extendee
            # If it's not concrete, then return the spec from the
            # extends() directive since that is all we know so far.
            spec_str, kwargs = next(iter(self.extendees.items()))
            return spack.spec.Spec(spec_str)

    @property
    def extendee_args(self):
        """
        Spec of the extendee of this package, or None if it is not an extension
        """
        if not self.extendees:
            return None

        # TODO: allow multiple extendees.
        name = next(iter(self.extendees))
        return self.extendees[name][1]

    @property
    def is_extension(self):
        # if it is concrete, it's only an extension if it actually
        # dependes on the extendee.
        if self.spec._concrete:
            return self.extendee_spec is not None
        else:
            # If not, then it's an extension if it *could* be an extension
            return bool(self.extendees)

    def extends(self, spec):
        """
        Returns True if this package extends the given spec.

        If ``self.spec`` is concrete, this returns whether this package extends
        the given spec.

        If ``self.spec`` is not concrete, this returns whether this package may
        extend the given spec.
        """
        if spec.name not in self.extendees:
            return False
        s = self.extendee_spec
        return s and spec.satisfies(s)

    def provides(self, vpkg_name):
        """
        True if this package provides a virtual package with the specified name
        """
        return any(
            any(self.spec.intersects(c) for c in constraints)
            for s, constraints in self.provided.items()
            if s.name == vpkg_name
        )

    @property
    def virtuals_provided(self):
        """
        virtual packages provided by this package with its spec
        """
        return [
            vspec
            for vspec, constraints in self.provided.items()
            if any(self.spec.satisfies(c) for c in constraints)
        ]

    @property
    def prefix(self):
        """Get the prefix into which this package should be installed."""
        return self.spec.prefix

    @property
    def home(self):
        return self.prefix

    @property  # type: ignore[misc]
    @memoized
    def compiler(self):
        """Get the spack.compiler.Compiler object used to build this package"""
        if not self.spec.concrete:
            raise ValueError("Can only get a compiler for a concrete package.")

        return spack.compilers.compiler_for_spec(self.spec.compiler, self.spec.architecture)

    def url_version(self, version):
        """
        Given a version, this returns a string that should be substituted
        into the package's URL to download that version.

        By default, this just returns the version string. Subclasses may need
        to override this, e.g. for boost versions where you need to ensure that
        there are _'s in the download URL.
        """
        return str(version)

    def remove_prefix(self):
        """
        Removes the prefix for a package along with any empty parent
        directories
        """
        spack.store.layout.remove_install_directory(self.spec)

    @property
    def download_instr(self):
        """
        Defines the default manual download instructions.  Packages can
        override the property to provide more information.

        Returns:
            (str):  default manual download instructions
        """
        required = (
            "Manual download is required for {0}. ".format(self.spec.name)
            if self.manual_download
            else ""
        )
        return "{0}Refer to {1} for download instructions.".format(
            required, self.spec.package.homepage
        )

    @classmethod
    def all_patches(cls):
        """Retrieve all patches associated with the package.

        Retrieves patches on the package itself as well as patches on the
        dependencies of the package."""
        patches = []
        for _, patch_list in cls.patches.items():
            for patch in patch_list:
                patches.append(patch)

        pkg_deps = cls.dependencies
        for dep_name in pkg_deps:
            for _, dependency in pkg_deps[dep_name].items():
                for _, patch_list in dependency.patches.items():
                    for patch in patch_list:
                        patches.append(patch)

        return patches

    def content_hash(self, content=None):
        """Create a hash based on the artifacts and patches used to build this package.

        This includes:
            * source artifacts (tarballs, repositories) used to build;
            * content hashes (``sha256``'s) of all patches applied by Spack; and
            * canonicalized contents the ``package.py`` recipe used to build.

        This hash is only included in Spack's DAG hash for concrete specs, but if it
        happens to be called on a package with an abstract spec, only applicable (i.e.,
        determinable) portions of the hash will be included.

        """
        # list of components to make up the hash
        hash_content = []

        # source artifacts/repositories
        # TODO: resources
        if self.spec.versions.concrete:
            try:
                source_id = fs.for_package_version(self).source_id()
            except (fs.ExtrapolationError, fs.InvalidArgsError):
                # ExtrapolationError happens if the package has no fetchers defined.
                # InvalidArgsError happens when there are version directives with args,
                #     but none of them identifies an actual fetcher.
                source_id = None

            if not source_id:
                # TODO? in cases where a digest or source_id isn't available,
                # should this attempt to download the source and set one? This
                # probably only happens for source repositories which are
                # referenced by branch name rather than tag or commit ID.
                env = spack.environment.active_environment()
                from_local_sources = env and env.is_develop(self.spec)
                if self.has_code and not self.spec.external and not from_local_sources:
                    message = "Missing a source id for {s.name}@{s.version}"
                    tty.debug(message.format(s=self))
                hash_content.append("".encode("utf-8"))
            else:
                hash_content.append(source_id.encode("utf-8"))

        # patch sha256's
        # Only include these if they've been assigned by the concretizer.
        # We check spec._patches_assigned instead of spec.concrete because
        # we have to call package_hash *before* marking specs concrete
        if self.spec._patches_assigned():
            hash_content.extend(
                ":".join((p.sha256, str(p.level))).encode("utf-8") for p in self.spec.patches
            )

        # package.py contents
        hash_content.append(package_hash(self.spec, source=content).encode("utf-8"))

        # put it all together and encode as base32
        b32_hash = base64.b32encode(
            hashlib.sha256(bytes().join(sorted(hash_content))).digest()
        ).lower()
        b32_hash = b32_hash.decode("utf-8")

        return b32_hash

    @property
    def cmake_prefix_paths(self):
        return [self.prefix]

    def _get_needed_resources(self):
        resources = []
        # Select the resources that are needed for this build
        if self.spec.concrete:
            for when_spec, resource_list in self.resources.items():
                if when_spec in self.spec:
                    resources.extend(resource_list)
        else:
            for when_spec, resource_list in self.resources.items():
                # Note that variant checking is always strict for specs where
                # the name is not specified. But with strict variant checking,
                # only variants mentioned in 'other' are checked. Here we only
                # want to make sure that no constraints in when_spec
                # conflict with the spec, so we need to invoke
                # when_spec.satisfies(self.spec) vs.
                # self.spec.satisfies(when_spec)
                if when_spec.intersects(self.spec):
                    resources.extend(resource_list)
        # Sorts the resources by the length of the string representing their
        # destination. Since any nested resource must contain another
        # resource's name in its path, it seems that should work
        resources = sorted(resources, key=lambda res: len(res.destination))
        return resources

    def _resource_stage(self, resource):
        pieces = ["resource", resource.name, self.spec.dag_hash()]
        resource_stage_folder = "-".join(pieces)
        return resource_stage_folder

    @classmethod
    def inject_flags(cls: Type, name: str, flags: Iterable[str]) -> FLAG_HANDLER_RETURN_TYPE:
        """
        flag_handler that injects all flags through the compiler wrapper.
        """
        return flags, None, None

    @classmethod
    def env_flags(cls: Type, name: str, flags: Iterable[str]):
        """
        flag_handler that adds all flags to canonical environment variables.
        """
        return None, flags, None

    @classmethod
    def build_system_flags(cls: Type, name: str, flags: Iterable[str]) -> FLAG_HANDLER_RETURN_TYPE:
        """
        flag_handler that passes flags to the build system arguments.  Any
        package using `build_system_flags` must also implement
        `flags_to_build_system_args`, or derive from a class that
        implements it.  Currently, AutotoolsPackage and CMakePackage
        implement it.
        """
        return None, None, flags

    _flag_handler: Optional[FLAG_HANDLER_TYPE] = None

    @property
    def flag_handler(self) -> FLAG_HANDLER_TYPE:
        if self._flag_handler is None:
            self._flag_handler = PackageBase.inject_flags
        return self._flag_handler

    @flag_handler.setter
    def flag_handler(self, var: FLAG_HANDLER_TYPE):
        self._flag_handler = var

    # The flag handler method is called for each of the allowed compiler flags.
    # It returns a triple of inject_flags, env_flags, build_system_flags.
    # The flags returned as inject_flags should be injected through
    #  compiler wrappers.
    # The flags returned as env_flags should be passed to the build
    #  system through environment variables of the same name.
    # The flags returned as build_system_flags should be passed to the
    #  build system package subclass to be turned into the appropriate
    #  part of the standard arguments. This is implemented for build
    #  system classes where appropriate and will otherwise raise a
    #  NotImplementedError.

    def flags_to_build_system_args(self, flags):
        # Takes flags as a dict name: list of values
        if any(v for v in flags.values()):
            msg = "The {0} build system".format(self.__class__.__name__)
            msg += " cannot take command line arguments for compiler flags"
            raise NotImplementedError(msg)

    def _check_extendable(self):
        if not self.extendable:
            raise ValueError("Package %s is not extendable!" % self.name)

    @classmethod
    def format_doc(cls, **kwargs):
        """Wrap doc string at 72 characters and format nicely"""
        indent = kwargs.get("indent", 0)

        if not cls.__doc__:
            return ""

        doc = re.sub(r"\s+", " ", cls.__doc__)
        lines = textwrap.wrap(doc, 72)
        results = io.StringIO()
        for line in lines:
            results.write((" " * indent) + line + "\n")
        return results.getvalue()

    @property
    def all_urls(self):
        """A list of all URLs in a package.

        Check both class-level and version-specific URLs.

        Returns:
            list: a list of URLs
        """
        urls = []
        if hasattr(self, "url") and self.url:
            urls.append(self.url)

        # fetch from first entry in urls to save time
        if hasattr(self, "urls") and self.urls:
            urls.append(self.urls[0])

        for args in self.versions.values():
            if "url" in args:
                urls.append(args["url"])
        return urls

    def fetch_remote_versions(self, concurrency=128):
        """Find remote versions of this package.

        Uses ``list_url`` and any other URLs listed in the package file.

        Returns:
            dict: a dictionary mapping versions to URLs
        """
        if not self.all_urls:
            return {}

        try:
            return spack.util.web.find_versions_of_archive(
                self.all_urls, self.list_url, self.list_depth, concurrency, reference_package=self
            )
        except spack.util.web.NoNetworkConnectionError as e:
            tty.die("Package.fetch_versions couldn't connect to:", e.url, e.message)

    @property
    def rpath(self):
        """Get the rpath this package links with, as a list of paths."""
        deps = self.spec.dependencies(deptype="link")

        # on Windows, libraries of runtime interest are typically
        # stored in the bin directory
        if sys.platform == "win32":
            rpaths = [self.prefix.bin]
            rpaths.extend(d.prefix.bin for d in deps if os.path.isdir(d.prefix.bin))
        else:
            rpaths = [self.prefix.lib, self.prefix.lib64]
            rpaths.extend(d.prefix.lib for d in deps if os.path.isdir(d.prefix.lib))
            rpaths.extend(d.prefix.lib64 for d in deps if os.path.isdir(d.prefix.lib64))
        return rpaths

    @property
    def rpath_args(self):
        """
        Get the rpath args as a string, with -Wl,-rpath, for each element
        """
        return " ".join("-Wl,-rpath,%s" % p for p in self.rpath)

