# bdk

This is part of a project to turn Blender into a viable level design tool for games running on Unreal Engine 2.

The purpose of this command line tool is to convert Unreal Engine 2 packages (e.g., `.usx`, `.utx` etc.) to `.blend` files that can be linked as asset libraries within Blender.

# Prerequisites
* Python 3.10+
* Blender 3.5.0+
* Umodel (build 1590)

# Installation

```commandline
mkdir C:\dev\bdk-git
cd C:\dev\bdk-git
git clone https://github.com/DarklightGames/bdk.git
cd bdk
.\bdk.py setup
```
