#!/bin/bash
# This script compiles ad flash the micropython firmware to the pyboard v1.1.
# To compile a module as frozen bytecode (to save ram), rename the "module_file.py" as "module_file.p_" in the firmware directory.
# To flash the firmware to the pyboard, it must be in DFU mode, to enter DFU mode, connect DFU pin with 3v3 and push reset button.
# Remember to enable _thread module in ports/stm32/mpconfigport.h
board="PYBV11"
source="$PWD/firmware"
dest="$PWD/micropython"
modules="/modules"
mpy="/mpy-cross"
port="/ports/stm32"
manifest="/boards/manifest.py"
rm -rv $dest$modules/*
for dir in $(find $source -type d); do
	cd $dir
	for file in $(find -maxdepth 1 -type f -name "*.p_"); do
		basename=$(basename $file)
		dirname=$(echo $(pwd) | sed 's|'$source'||g')
		mkdir -p $dest$modules$dirname
		cp -fv $(pwd)/$basename $dest$modules$dirname/$basename
		mv -v $dest$modules$dirname/$basename $dest$modules$dirname/$(basename $basename .p_).py
		done
	done
cd $dest
rm -v $dest$port$manifest
for dir in $(find $dest$modules -type d); do
	cd $dir
	for file in $(find -maxdepth 1 -type f -name "*.py"); do
		echo freeze\(\'\$\(MPY_DIR\)\/$(basename $modules)\', \'$(echo $dir/$(basename $file) | sed 's|'$dest$modules/'||g')\'\) >> $dest$port$manifest		
		done
	done
cd $dest$mpy
make
cd $dest$port
make submodules
make BOARD=$board clean
make BOARD=$board 
make BOARD=$board deploy
