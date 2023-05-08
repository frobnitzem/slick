#!/bin/bash
# Install clingo into your venv

if [ -z "$VIRTUAL_ENV" ] || [ ! -x "$VIRTUAL_ENV/bin/python" ]; then
	echo "You must be inside a virtual environment to install this."
	exit 1
fi

dir="`mktemp -d`"
cwd="`pwd`"
cd "$dir"
    curl -L -O https://github.com/potassco/clingo/archive/v5.5.0.tar.gz && \
    tar xzf v5.5.0.tar.gz && \
	mkdir build && cd build && \
    cmake "-DCMAKE_INSTALL_PREFIX=$VIRTUAL_ENV" ../clingo-* \
	&& make -j8 install
ret=$?
cd "$cwd"
rm -fr "$dir"
exit $ret
