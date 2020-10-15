CMAKE_COMMON_VARIABLES=" -DCMAKE_INSTALL_PREFIX=$PREFIX \
0;95;0c    -DCMAKE_BUILD_TYPE=Release -DLLVM_TARGETS_TO_BUILD=host \
    -DLLVM_INCLUDE_TESTS=OFF -DLLVM_INCLUDE_UTILS=OFF \
    -DLLVM_INCLUDE_DOCS=OFF -DLLVM_INCLUDE_EXAMPLES=OFF \
    "

platform='unknown'
unamestr="$(uname)"

if [[ "$unamestr" == 'Linux' ]]; then
    platform='linux'
elif [[ "$unamestr" == 'FreeBSD' ]]; then
    platform='freebsd'
elif [[ "$unamestr" == 'Darwin' ]]; then
    platform='osx'
fi

# If available, enable newer toolset on old RH / CentOS machines
toolset=/opt/rh/devtoolset-2

if [ -d $toolset ]; then
    . /opt/rh/devtoolset-2/enable
    export CC=gcc
    export CXX=g++
fi

if [ -n "$MACOSX_DEPLOYMENT_TARGET" ]; then
    # OSX needs 10.7 or above with libc++ enabled
    export MACOSX_DEPLOYMENT_TARGET=10.9
fi

# Use CMake-based build procedure
mkdir build
cd build
if [[ "$platform" == 'linux' ]]; then
    cmake $CMAKE_COMMON_VARIABLES -DLLVM_USE_OPROFILE=ON ..
else
    cmake $CMAKE_COMMON_VARIABLES ..
fi

make -j4
make install
