import os

RFB_ADDON_VERSION_MAJOR = 24
RFB_ADDON_VERSION_MINOR = 0
RFB_ADDON_VERSION_PATCH = 0
RFB_ADDON_VERSION = (RFB_ADDON_VERSION_MAJOR, RFB_ADDON_VERSION_MINOR, RFB_ADDON_VERSION_PATCH)
RFB_ADDON_VERSION_STRING = '%d.%d.%d' % (RFB_ADDON_VERSION_MAJOR, RFB_ADDON_VERSION_MINOR, RFB_ADDON_VERSION_PATCH)
RFB_ADDON_PATH = os.path.dirname(os.path.abspath(__file__))

BLENDER_SUPPORTED_VERSION_MAJOR = 2
BLENDER_SUPPORTED_VERSION_MINOR = 80
BLENDER_SUPPORTED_VERSION_PATCH = 0
BLENDER_SUPPORTED_VERSION = (BLENDER_SUPPORTED_VERSION_MAJOR, BLENDER_SUPPORTED_VERSION_MINOR, BLENDER_SUPPORTED_VERSION_PATCH)

RMAN_SUPPORTED_VERSION_MAJOR = 24
RMAN_SUPPORTED_VERSION_MINOR = 0
RMAN_SUPPORTED_VERSION_BETA = ''
RMAN_SUPPORTED_VERSION = (RMAN_SUPPORTED_VERSION_MAJOR, RMAN_SUPPORTED_VERSION_MINOR, RMAN_SUPPORTED_VERSION_BETA)
RMAN_SUPPORTED_VERSION_STRING = '%d.%d%s' % (RMAN_SUPPORTED_VERSION_MAJOR, RMAN_SUPPORTED_VERSION_MINOR, RMAN_SUPPORTED_VERSION_BETA)


RFB_ADDON_DESCRIPTION = 'RenderMan %d.%d integration' % (RMAN_SUPPORTED_VERSION_MAJOR, RMAN_SUPPORTED_VERSION_MINOR)

NODE_LAYOUT_SPLIT = 0.5
RFB_ARRAYS_MAX_LEN = 50
RFB_MAX_USER_TOKENS = 10
RFB_VIEWPORT_MAX_BUCKETS = 10
RFB_PREFS_NAME = "RenderManForBlender"

RFB_FLOAT3 = ['color', 'point', 'vector', 'normal']
RFB_FLOATX = ['color', 'point', 'vector', 'normal', 'matrix']

RMAN_STYLIZED_FILTERS = [
    "PxrStylizedHatching",
    "PxrStylizedLines",
    "PxrStylizedToon"
]    

RMAN_STYLIZED_PATTERNS = ["PxrStylizedControl"]
RMAN_UTILITY_PATTERN_NAMES = [
                            "utilityPattern",
                            "userColor",
                            "inputAOV",
                            "utilityInteger"]

# special string to indicate an empty string
# necessary for EnumProperty because it cannot
# take an empty string as an item value
__RMAN_EMPTY_STRING__ = '__empty__'

# these are reserved property names for Blender's nodes
__RESERVED_BLENDER_NAMES__ = {
    'dimensions' : 'rman_dimensions',
    'inputs': 'rman_inputs',
    'outputs': 'rman_outputs',
    'resolution': 'rman_resolution'
}