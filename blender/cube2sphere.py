import sys
import bpy
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('front')
parser.add_argument('back')
parser.add_argument('right')
parser.add_argument('left')
parser.add_argument('top')
parser.add_argument('bottom')
parser.add_argument('--output', required=False, default='./output.tga')
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])

bpy.data.images['front'].filepath = args.front
bpy.data.images['back'].filepath = args.back
bpy.data.images['right'].filepath = args.right
bpy.data.images['left'].filepath = args.left
bpy.data.images['top'].filepath = args.top
bpy.data.images['bottom'].filepath = args.bottom

bpy.context.scene.render.filepath = args.output

bpy.ops.render.render(write_still=True)
