from .directives import DirectiveMeta

class PackageBase(metaclass=DirectiveMeta):
    def __init__(self):
        super(PackageBase, self).__init__()

