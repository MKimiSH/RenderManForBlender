from . import string_utils
from . import property_utils
from . import shadergraph_utils
from . import scene_utils
from .. import rman_constants
from .. import rman_config
from collections import OrderedDict
from copy import deepcopy
import bpy
import os
import getpass

__BLENDER_TO_RMAN_DSPY__ = { 'TIFF': 'tiff', 'TARGA': 'targa', 'TARGA_RAW': 'targa', 'OPEN_EXR': 'openexr', 'PNG': 'png'}

def get_channel_name(aov, layer_name):
    aov_name = aov.name.replace(' ', '')
    aov_channel_name = aov.channel_name
    if not aov.aov_name or not aov.channel_name:
        return ''
    elif aov.aov_name == "color rgba":
        aov_channel_name = "Ci,a"
    # Remaps any color lpe channel names to a denoise friendly one
    elif aov_name in channel_name_map.keys():
        aov_channel_name = '%s_%s_%s' % (
            channel_name_map[aov_name], aov_name, layer_name)

    elif aov.aov_name == "color custom_lpe":
        aov_channel_name = aov.name

    else:
        aov_channel_name = '%s_%s' % (
            aov_name, layer_name)

    return aov_channel_name

def _default_dspy_params():
    d = {}
    d[u'enable'] = { 'type': u'int', 'value': True}
    d[u'lpeLightGroup'] = { 'type': u'string', 'value': None}
    d[u'remap_a'] = { 'type': u'float', 'value': 0.0}
    d[u'remap_b'] = { 'type': u'float', 'value': 0.0}
    d[u'remap_c'] = { 'type': u'float', 'value': 0.0}  
    d[u'exposure'] = { 'type': u'float2', 'value': [1.0, 1.0] }
    d[u'filter'] = {'type': u'string', 'value': 'default'}
    d[u'filterwidth'] = { 'type': u'float2', 'value': [2,2]}   
    d[u'statistics'] = { 'type': u'string', 'value': 'none'}
    d[u'shadowthreshold'] = { 'type': u'float', 'value': 0.01} 

    return d    

def _add_stylized_channels(dspys_dict, dspy_drv, rman_scene, expandTokens):
    """
    Add the necessary dspy channels for stylized looks. 
    """ 
    stylized_tmplt = rman_config.__RMAN_DISPLAY_TEMPLATES__.get('Stylized', None)
    if not stylized_tmplt:
        return  

    rm = rman_scene.bl_scene.renderman
    display_driver = dspy_drv
    rman_dspy_channels = rman_config.__RMAN_DISPLAY_CHANNELS__

    if not display_driver:
        display_driver = __BLENDER_TO_RMAN_DSPY__.get(rman_scene.bl_scene.render.image_settings.file_format, 'openexr')
        if 'display' in stylized_tmplt:
            display_driver = stylized_tmplt['display']['displayType']        

    if display_driver in ['it', 'blender']:
        if rman_scene.is_viewport_render:
            display_driver = 'null'

        for chan in stylized_tmplt['channels']:
            dspy_params = {}                        
            dspy_params['displayChannels'] = []
            dspy_name = '%s_%s' % (stylized_tmplt.get('displayName', 'rman_stylized'), chan)

            d = _default_dspy_params()
            if chan not in dspys_dict['channels']:
                d = _default_dspy_params()
                settings = rman_dspy_channels[chan]
                chan_src = settings['channelSource']
                chan_type = settings['channelType']
                d[u'channelSource'] = {'type': u'string', 'value': chan_src}
                d[u'channelType'] = { 'type': u'string', 'value': chan_type}                  
                dspys_dict['channels'][chan] = d
            dspy_params['displayChannels'].append(chan)

            filePath = '%s_%s' % (dspy_name, chan)         

            dspys_dict['displays'][dspy_name] = {
                'driverNode': display_driver,
                'filePath': filePath,
                'denoise': False,
                'denoise_mode': 'singleframe',   
                'camera': None,  
                'bake_mode': None,                   
                'params': dspy_params,
                'dspyDriverParams': None}        
    else:
        dspy_name = stylized_tmplt.get('displayName', 'rman_stylized')
        dspy_params = {}                        
        dspy_params['displayChannels'] = []

        for chan in stylized_tmplt['channels']:
            d = _default_dspy_params()
            if chan not in dspys_dict['channels']:
                d = _default_dspy_params()
                settings = rman_dspy_channels[chan]
                chan_src = settings['channelSource']
                chan_type = settings['channelType']
                d[u'channelSource'] = {'type': u'string', 'value': chan_src}
                d[u'channelType'] = { 'type': u'string', 'value': chan_type}                  
                dspys_dict['channels'][chan] = d
            dspy_params['displayChannels'].append(chan)

        filePath = rm.path_beauty_image_output
        f, ext = os.path.splitext(filePath)
        filePath = f + '_rman_stylized' + ext      
        if expandTokens:      
            filePath = string_utils.expand_string(filePath,
                                                display=display_driver, 
                                                frame=rman_scene.bl_frame_current,
                                                asFilePath=True)            

        dspys_dict['displays'][dspy_name] = {
            'driverNode': display_driver,
            'filePath': filePath,
            'denoise': False,
            'denoise_mode': 'singleframe',   
            'camera': None,  
            'bake_mode': None,                   
            'params': dspy_params,
            'dspyDriverParams': None}                    

def _add_denoiser_channels(dspys_dict, dspy_params):
    """
    Add the necessary dspy channels for denoiser. We assume
    the beauty display will be used as the variance file
    """

    denoise_tmplt = rman_config.__RMAN_DISPLAY_TEMPLATES__['Variance']
    for chan in denoise_tmplt['channels']:
        dspy_channels = dspys_dict['displays']['beauty']['params']['displayChannels']
        if chan in dspy_channels:
            continue

        if chan not in dspys_dict['channels']:
            d = _default_dspy_params()
            settings = rman_config.__RMAN_DISPLAY_CHANNELS__[chan]

            d[u'channelSource'] = {'type': u'string', 'value': settings['channelSource']}
            d[u'channelType'] = { 'type': u'string', 'value': settings['channelType']}
            if 'statistics' in settings:
                d[u'statistics'] = { 'type': u'string', 'value': settings['statistics']}
            dspys_dict['channels'][chan] =  d  

        dspys_dict['displays']['beauty']['params']['displayChannels'].append(chan)            

    filePath = dspys_dict['displays']['beauty']['filePath']
    f,ext = os.path.splitext(filePath)
    dspys_dict['displays']['beauty']['filePath'] = f + '_variance' + ext

def _set_blender_dspy_dict(layer, dspys_dict, dspy_drv, rman_scene, expandTokens, do_optix_denoise=False):   

    rm = rman_scene.bl_scene.renderman
    display_driver = dspy_drv
    param_list = None
    aov_denoise = False

    if not display_driver:
        display_driver = __BLENDER_TO_RMAN_DSPY__.get(rman_scene.bl_scene.render.image_settings.file_format, 'openexr')
        param_list = rman_scene.rman.Types.ParamList()
        if display_driver == 'openexr':
            param_list.SetInteger('asrgba', 1)

    if display_driver == 'blender' and do_optix_denoise:   
        aov_denoise = True
        param_list = rman_scene.rman.Types.ParamList()     
        param_list.SetInteger("use_optix_denoiser", 1)        

    # add beauty (Ci,a)
    dspy_params = {}                        
    dspy_params['displayChannels'] = []

    d = _default_dspy_params()
    d[u'channelSource'] = {'type': u'string', 'value': 'Ci'}
    d[u'channelType'] = { 'type': u'string', 'value': 'color'}       
    dspys_dict['channels']['Ci'] = d
    d = _default_dspy_params()
    d[u'channelSource'] = {'type': u'string', 'value': 'a'}
    d[u'channelType'] = { 'type': u'string', 'value': 'float'}          
    dspys_dict['channels']['a'] = d     
    dspy_params['displayChannels'].append('Ci')
    dspy_params['displayChannels'].append('a')
    filePath = rm.path_beauty_image_output
    if expandTokens:
        filePath = string_utils.expand_string(filePath,
                                            display=display_driver, 
                                            frame=rman_scene.bl_frame_current,
                                            asFilePath=True)
    dspys_dict['displays']['beauty'] = {
        'driverNode': display_driver,
        'filePath': filePath,
        'denoise': aov_denoise,
        'denoise_mode': 'singleframe',
        'camera': None,
        'bake_mode': None,            
        'params': dspy_params,
        'dspyDriverParams': param_list}

    if display_driver == 'blender' and rman_scene.is_viewport_render:
            display_driver = 'null' 

    # so use built in aovs
    blender_aovs = [
        ('zfiltered', layer.use_pass_z, 'Depth'),
        ('Nn', layer.use_pass_normal, "Normal"),
        ("dPdtime", layer.use_pass_vector, "dPdtime"),
        ("st", layer.use_pass_uv, "UV"),
        ("id", layer.use_pass_object_index, "IndexOB"),
        ("blender_shadows", layer.use_pass_ambient_occlusion, "AO"),
        ("blender_diffuse", layer.use_pass_diffuse_direct, "DiffDir"),
        ("blender_indirectdiffuse", layer.use_pass_diffuse_indirect, "DiffInd"),
        ("blender_albedo", layer.use_pass_diffuse_color, "DiffCol"),
        ("blender_specular", layer.use_pass_glossy_direct, "GlossDir"),
        ("blender_indirectspecular", layer.use_pass_glossy_indirect, "GlossInd"),
        ("blender_subsurface", layer.use_pass_subsurface_indirect,"SubsurfaceInd"),
        ("blender_emission", layer.use_pass_emit, "Emit")
    ]     


    # declare display channels
    for source, doit, name in blender_aovs:
        filePath = rm.path_aov_image_output
        if expandTokens:
            token_dict = {'aov': name}
            filePath = string_utils.expand_string(filePath, 
                                                display=display_driver, 
                                                frame=rman_scene.bl_frame_current,
                                                token_dict=token_dict,
                                                asFilePath=True)
        if doit:
            dspy_params = {}                        
            dspy_params['displayChannels'] = []
            
            d = _default_dspy_params()
            settings = rman_config.__RMAN_DISPLAY_CHANNELS__[source]

            d[u'channelSource'] = {'type': u'string', 'value': settings['channelSource']}
            d[u'channelType'] = { 'type': u'string', 'value': settings['channelType']}     
            if source == 'id':
                d[u'filter'] = {'type': u'string', 'value': 'zmin'}
                d[u'filterwidth'] = { 'type': u'float2', 'value': [1, 1]}             

            dspys_dict['channels'][name] = d
            dspy_params['displayChannels'].append(name)
            dspys_dict['displays'][name] = {
            'driverNode': display_driver,
            'filePath': filePath,
            'denoise': aov_denoise,
            'denoise_mode': 'singleframe',  
            'camera': None, 
            'bake_mode': None,                
            'params': dspy_params,
            'dspyDriverParams': param_list}   

    if not layer.use_pass_object_index and rman_scene.is_interactive:
        # Add ID pass if it was not requested and we're in
        # IPR mode
        dspy_params = {}                        
        dspy_params['displayChannels'] = []            
        d = _default_dspy_params()
        d[u'channelSource'] = {'type': u'string', 'value': 'id'}
        d[u'channelType'] = { 'type': u'string', 'value': 'integer'}        
        d[u'filter'] = {'type': u'string', 'value': 'zmin'}
        d[u'filterwidth'] = { 'type': u'float2', 'value': [1, 1]}                       
        dspys_dict['channels']['id'] = d     
        dspy_params['displayChannels'].append('id')
        filePath = 'id_pass'
        
        dspys_dict['displays']['id_pass'] = {
            'driverNode': display_driver,
            'filePath': filePath,
            'denoise': False,
            'denoise_mode': 'singleframe',  
            'camera': None,    
            'bake_mode': None,          
            'params': dspy_params,
            'dspyDriverParams': None}                     

def _get_real_chan_name(chan):
    """ Get the real channel name
    Channels with a light group will have the light group
    appended to the name
    """
    ch_name = chan.channel_name
    lgt_grp = chan.light_group.strip()
    if lgt_grp != '' and lgt_grp not in ch_name:
        ch_name = '%s_%s' % (ch_name, lgt_grp)   
    return ch_name

def _add_chan_to_dpsychan_list(rm, rm_rl, dspys_dict, chan):

    ch_name = _get_real_chan_name(chan)
    lgt_grp = chan.light_group.strip()
    # add the channel if not already in list            
    if ch_name not in dspys_dict['channels']:
        d = _default_dspy_params()                
        source_type = chan.channel_type
        source = chan.channel_source

        if lgt_grp or lgt_grp != '':
            if 'Ci' in source:
                source = "lpe:C[DS]*[<L.>O]"
            if "<L.>" in source:
                source = source.replace("<L.>", "<L.'%s'>" % lgt_grp)
            elif "lpe:" in source:
                source = source.replace("L", "<L.'%s'>" % lgt_grp)

        d[u'channelSource'] = {'type': u'string', 'value': source}
        d[u'channelType'] = { 'type': u'string', 'value': source_type}
        d[u'lpeLightGroup'] = { 'type': u'string', 'value': lgt_grp}
        d[u'remap_a'] = { 'type': u'float', 'value': chan.remap_a}
        d[u'remap_b'] = { 'type': u'float', 'value': chan.remap_b}
        d[u'remap_c'] = { 'type': u'float', 'value': chan.remap_c}
        d[u'exposure'] = { 'type': u'float2', 'value': [chan.exposure_gain, chan.exposure_gamma] }

        if rm.hider_pixelFilterMode != 'importance':
            # per channel filter does not work in importance mode
            d[u'filter'] = {'type': u'string', 'value': chan.chan_pixelfilter}
            d[u'filterwidth'] = { 'type': u'float2', 'value': [chan.chan_pixelfilter_x, chan.chan_pixelfilter_y]}

        d[u'statistics'] = { 'type': u'string', 'value': chan.stats_type}
        d[u'shadowthreshold'] = { 'type': u'float', 'value': chan.shadowthreshold}
        dspys_dict['channels'][ch_name] = d      
    

def _set_rman_dspy_dict(rm_rl, dspys_dict, dspy_drv, rman_scene, expandTokens, do_optix_denoise=False):

    rm = rman_scene.bl_scene.renderman
    display_driver = dspy_drv

    for aov in rm_rl.custom_aovs:
        if aov.name == '':
            continue
        if len(aov.dspy_channels) < 1:
            continue

        dspy_params = {}            
        dspy_params['displayChannels'] = []

        for chan_ptr in aov.dspy_channels:
            chan = rm_rl.dspy_channels[chan_ptr.dspy_chan_idx]
            _add_chan_to_dpsychan_list(rm, rm_rl, dspys_dict, chan)
            dspy_params['displayChannels'].append(chan.channel_name)

        param_list = None
        aov_denoise = aov.denoise
        aov_denoise_mode = aov.denoise_mode
        if rman_scene.rman_bake:
            if rm.rman_bake_illum_mode == '3D':
                display_driver = 'pointcloud'
            else:
                display_driver = aov.displaydriver

                param_list = rman_scene.rman.Types.ParamList()
                dspy_driver_settings = getattr(aov, '%s_settings' % display_driver)
                property_utils.set_node_rixparams(dspy_driver_settings, None, param_list, None)                
        elif rman_scene.external_render:
            display_driver = aov.displaydriver

            param_list = rman_scene.rman.Types.ParamList()
            dspy_driver_settings = getattr(aov, '%s_settings' % display_driver)
            property_utils.set_node_rixparams(dspy_driver_settings, None, param_list, None)            
        elif display_driver == 'blender': 
            if rman_scene.is_viewport_render:
                if aov.name != 'beauty':
                    display_driver = 'null'   
            if display_driver == 'blender' and do_optix_denoise:
                aov_denoise = True
                param_list = rman_scene.rman.Types.ParamList()
                param_list.SetInteger("use_optix_denoiser", 1)

        if rman_scene.rman_bake:            
            filePath = rm.path_bake_illum_ptc
            if rm.rman_bake_illum_mode == '2D':
                filePath = rm.path_bake_illum_img                
            if expandTokens:                 
                token_dict = {'aov': aov.name}
                filePath = string_utils.expand_string(filePath, 
                                                display=display_driver, 
                                                frame=rman_scene.bl_frame_current,
                                                token_dict=token_dict,
                                                asFilePath=True)     

            if rm.rman_bake_illum_filename == 'BAKEFILEATTR':
                filePath = '<user:bake_filename_attr>'

            elif rm.rman_bake_illum_filename == 'IDENTIFIER':
                tokens = os.path.splitext(filePath)
                filePath = '%s.<identifier:object>%s' % (tokens[0], tokens[1])
                   
        else:       
            if aov.name == 'beauty':
                filePath = rm.path_beauty_image_output
                if expandTokens:
                    filePath = string_utils.expand_string(filePath,
                                                    display=display_driver, 
                                                    frame=rman_scene.bl_frame_current,
                                                    asFilePath=True)
            else:
                filePath = rm.path_aov_image_output
                if expandTokens:                 
                    token_dict = {'aov': aov.name}
                    filePath = string_utils.expand_string(filePath, 
                                                    display=display_driver, 
                                                    frame=rman_scene.bl_frame_current,
                                                    token_dict=token_dict,
                                                    asFilePath=True)

        if aov.name != 'beauty' and (display_driver in ['it', 'blender']): #(display_driver == 'it' or rman_scene.is_viewport_render):
            # break up display per channel when rendering to it
            if len(aov.dspy_channels) == 1:
                dspys_dict['displays'][aov.name] = {
                    'driverNode': display_driver,
                    'filePath': filePath,
                    'denoise': aov_denoise,
                    'denoise_mode': aov_denoise_mode,
                    'camera': aov.camera,
                    'bake_mode': aov.aov_bake,
                    'params': dspy_params,
                    'dspyDriverParams': param_list }         
            else:       
                for chan_ptr in aov.dspy_channels:
                    chan = rm_rl.dspy_channels[chan_ptr.dspy_chan_idx]
                    ch_name = _get_real_chan_name(chan)
                    dspy_name = '%s_%s' % (aov.name, ch_name)
                    new_dspy_params = deepcopy(dspy_params)
                    new_dspy_params['displayChannels'] = [ch_name]
                    if display_driver == 'it':
                        new_file_path = filePath.replace('.it', '_%s.it' % ch_name)
                    else:
                        new_file_path = filePath.replace('.exr', '_%s.exr' % ch_name)

                    dspys_dict['displays'][dspy_name] = {
                        'driverNode': display_driver,
                        'filePath': new_file_path,
                        'denoise': aov_denoise,
                        'denoise_mode': aov_denoise_mode,
                        'camera': aov.camera,
                        'bake_mode': aov.aov_bake,
                        'params': new_dspy_params,
                        'dspyDriverParams': param_list }

        else:
            dspys_dict['displays'][aov.name] = {
                'driverNode': display_driver,
                'filePath': filePath,
                'denoise': aov_denoise,
                'denoise_mode': aov_denoise_mode,
                'camera': aov.camera,
                'bake_mode': aov.aov_bake,
                'params': dspy_params,
                'dspyDriverParams': param_list }

        if aov_denoise and display_driver == 'openexr' and not rman_scene.is_interactive:
            _add_denoiser_channels(dspys_dict, dspy_params)

        if aov.name == 'beauty' and rman_scene.is_interactive:
          
            if rman_scene.is_viewport_render:
                display_driver = 'null'

            # Add ID pass
            dspy_params = {}                        
            dspy_params['displayChannels'] = []            
            d = _default_dspy_params()
            d[u'channelSource'] = {'type': u'string', 'value': 'id'}
            d[u'channelType'] = { 'type': u'string', 'value': 'integer'}     
            d[u'filter'] = {'type': u'string', 'value': 'zmin'}
            d[u'filterwidth'] = { 'type': u'float2', 'value': [1, 1]}            
            dspys_dict['channels']['id'] = d     
            dspy_params['displayChannels'].append('id')
            filePath = 'id_pass'
            
            dspys_dict['displays']['id_pass'] = {
                'driverNode': display_driver,
                'filePath': filePath,
                'denoise': False,
                'denoise_mode': 'singleframe',
                'camera': aov.camera,
                'bake_mode': None,
                'params': dspy_params,
                'dspyDriverParams': None}  

def _set_rman_holdouts_dspy_dict(dspys_dict, dspy_drv, rman_scene, expandTokens):

    rm = rman_scene.bl_scene.renderman
    display_driver = dspy_drv

    if not display_driver:
        display_driver = __BLENDER_TO_RMAN_DSPY__.get(rman_scene.bl_scene.render.image_settings.file_format, 'openexr')
        param_list = rman_scene.rman.Types.ParamList()
        if display_driver == 'openexr':
            param_list.SetInteger('asrgba', 1)

    dspy_params = {}                        
    dspy_params['displayChannels'] = []
    d = _default_dspy_params()
    occluded_src = "color lpe:holdouts;C[DS]+<L.>"
    d[u'channelSource'] = {'type': u'string', 'value': occluded_src}
    d[u'channelType'] = { 'type': u'string', 'value': 'color'}       
    dspys_dict['channels']['occluded'] = d
    dspy_params['displayChannels'].append('occluded')

    dspys_dict['displays']['occluded'] = {
        'driverNode': 'null',
        'filePath': 'occluded',
        'denoise': False,
        'denoise_mode': 'singleframe',   
        'camera': None,  
        'bake_mode': None,                   
        'params': dspy_params,
        'dspyDriverParams': None}        

    dspy_params = {}                        
    dspy_params['displayChannels'] = []
    d = _default_dspy_params()
    holdout_matte_src = "color lpe:holdouts;unoccluded;C[DS]+<L.>"
    d[u'channelSource'] = {'type': u'string', 'value': holdout_matte_src}
    d[u'channelType'] = { 'type': u'string', 'value': 'color'}          
    dspys_dict['channels']['holdoutMatte'] = d   
    dspy_params['displayChannels'].append('holdoutMatte')

    # user wants separate AOV for matte
    if rm.do_holdout_matte == "AOV":
        filePath = rm.path_beauty_image_output
        f, ext = os.path.splitext(filePath)
        filePath = f + '_holdoutMatte' + ext      
        if expandTokens:      
            filePath = string_utils.expand_string(filePath,
                                                display=display_driver, 
                                                frame=rman_scene.bl_frame_current,
                                                asFilePath=True)

        dspys_dict['displays']['holdoutMatte'] = {
            'driverNode': display_driver,
            'filePath': filePath,
            'denoise': False,
            'denoise_mode': 'singleframe',
            'camera': None,
            'bake_mode': None,                
            'params': dspy_params,
            'dspyDriverParams': None}
    else:
        dspys_dict['displays']['holdoutMatte'] = {
            'driverNode': 'null',
            'filePath': 'holdoutMatte',
            'denoise': False,
            'denoise_mode': 'singleframe',
            'camera': None,
            'bake_mode': None,                
            'params': dspy_params,
            'dspyDriverParams': None}                    

def get_dspy_dict(rman_scene, expandTokens=True):
    """
    Create a dictionary of display channels and displays. The layout:

        { 'channels': {
        u'Ci': { u'channelSource': { 'type': u'string', 'value': u'Ci'},
                 u'channelType': { 'type': u'string', 'value': u'color'},
                 u'enable': { 'type': u'int', 'value': True},
                 u'lpeLightGroup': { 'type': u'string', 'value': None},
                 u'remap_a': { 'type': u'float', 'value': 0.0},
                 u'remap_b': { 'type': u'float', 'value': 0.0},
                 u'remap_c': { 'type': u'float', 'value': 0.0}
               },
        u'a': { u'channelSource': { 'type': u'string', 'value': u'a'},
                u'channelType': { 'type': u'string', 'value': u'float'},
                u'enable': { 'type': u'int', 'value': True},
                u'lpeLightGroup': { 'type': u'string', 'value': None},
                u'remap_a': { 'type': u'float', 'value': 0.0},
                u'remap_b': { 'type': u'float', 'value': 0.0},
                u'remap_c': { 'type': u'float', 'value': 0.0}
              }
      },
      'displays': { u'rmanDefaultDisplay':
                      { 'driverNode': u'd_openexr1',
                        'filePath': u'<OUT>/<blender>/images/<scene>.<F4>.<ext>',
                        'params': { u'enable': { 'type': u'int', 'value': True},
                                    u'displayChannels': { 'type': u'message', 'value': [ u'Ci', u'a']},
                                    u'displayType': { 'type': u'message', 'value': u'd_openexr'},
                                    u'exposure': { 'type': u'float2', 'value': [1.0, 1.0]},
                                    u'filter': { 'type': u'string', 'value': 'default},
                                    u'filterwidth': { 'type': u'float2', 'value': [1.0, 1.0]},
                                    u'remap_a': { 'type': u'float', 'value': 0.0},
                                    u'remap_b': { 'type': u'float', 'value': 0.0},
                                    u'remap_c': { 'type': u'float', 'value': 0.0}
                                  },
                        'camera': [None|u'camera_name'],
                        'denoise': [True|False],
                        'denoise_mode': [u'singleframe'|u'crossframe']
                        'bake_mode': [True|False]
                        'dspyDriverParams': RtParamList
                      }
                  }
        }

    """

    rm = rman_scene.bl_scene.renderman
    rm_rl = rman_scene.rm_rl
    layer = rman_scene.bl_view_layer
    if not layer:
        layer = bpy.context.view_layer

    dspys_dict = {'displays': OrderedDict(), 'channels': {}}
    display_driver = None
    do_optix_denoise = False

    if rman_scene.is_interactive:
        display_driver = rm.render_ipr_into
        do_optix_denoise = rm.blender_ipr_optix_denoiser

    elif (not rman_scene.external_render): 
        # if preview render
        # we ignore the display driver setting in the AOV and render to whatever
        # render_into is set to
        display_driver = rm.render_into
        do_optix_denoise = rm.blender_optix_denoiser

    if rm.render_rman_stylized:
        _add_stylized_channels(dspys_dict, display_driver, rman_scene, expandTokens)        
       
    if rm_rl:     
        _set_rman_dspy_dict(rm_rl, dspys_dict, display_driver, rman_scene, expandTokens, do_optix_denoise=do_optix_denoise)        

    else:
        # We're using blender's layering system
        _set_blender_dspy_dict(layer, dspys_dict, display_driver, rman_scene, expandTokens, do_optix_denoise=do_optix_denoise)       

    if rm.do_holdout_matte != "OFF":
        _set_rman_holdouts_dspy_dict(dspys_dict, display_driver, rman_scene, expandTokens)  

    return dspys_dict


def make_dspy_info(scene):
    """
    Create some render parameter from scene and pass it to image tool.

    If current scene renders to "it", collect some useful infos from scene
    and send them alongside the render job to RenderMan's image tool. Applies to
    renderpass result only, does not affect postprocessing like denoise.

    Arguments:
        scene (bpy.types.Scene) - Blender scene object

    Returns:
        (str) - a string with the display notes to give to "it"

    """
    params = {}
    rm = scene.renderman
    world = scene.world
    from time import localtime, strftime
    ts = strftime("%a %x, %X", localtime())
    ts = bytes(ts, 'ascii', 'ignore').decode('utf-8', 'ignore')
    integrator = shadergraph_utils.find_integrator_node(world)
    integrator_nm = 'PxrPathTracer'
    if integrator:
        integrator_nm = integrator.bl_label

    dspy_notes = "Render start:\t%s\r\r" % ts
    dspy_notes += "Integrator:\t%s\r\r" % integrator_nm
    dspy_notes += "Samples:\t%d - %d\r" % (rm.hider_minSamples, rm.hider_maxSamples)
    dspy_notes += "Pixel Variance:\t%f\r\r" % rm.ri_pixelVariance

    # moved this in front of integrator check. Was called redundant in
    # both cases
    if integrator:    
        if integrator.bl_label == 'PxrPathTracer':
            dspy_notes += "Mode:\t%s\r" % integrator.sampleMode
            dspy_notes += "Light:\t%d\r" % integrator.numLightSamples
            dspy_notes += "Bxdf:\t%d\r" % integrator.numBxdfSamples

            if integrator.sampleMode == 'bxdf':
                dspy_notes += "Indirect:\t%d\r\r" % integrator.numIndirectSamples
            else:
                dspy_notes += "Diffuse:\t%d\r" % integrator.numDiffuseSamples
                dspy_notes += "Specular:\t%d\r" % integrator.numSpecularSamples
                dspy_notes += "Subsurface:\t%d\r" % integrator.numSubsurfaceSamples
                dspy_notes += "Refraction:\t%d\r" % integrator.numRefractionSamples

        elif integrator.bl_label == "PxrVCM":
            dspy_notes += "Light:\t%d\r" % integrator.numLightSamples
            dspy_notes += "Bxdf:\t%d\r\r" % integrator.numBxdfSamples

    return dspy_notes

def export_metadata(scene, params, camera_name=None):
    """
    Create metadata for the OpenEXR display driver

    Arguments:
        scene (bpy.types.Scene) - Blender scene object
        params (RtParamList) - param list to fill with meta data
        camera_name - Name of camera we want meta data from
    """

    rm = scene.renderman
    world = scene.world         
    output_dir = string_utils.expand_string(rm.path_rib_output, 
                                            frame=scene.frame_current, 
                                            asFilePath=True)  
    output_dir = os.path.dirname(output_dir)
    statspath=os.path.join(output_dir, 'stats.%04d.xml' % scene.frame_current)

    params.SetString('exrheader_dcc', 'Blender %s\nRenderman for Blender %s' % (bpy.app.version, rman_constants.RFB_ADDON_VERSION_STRING))



    params.SetString('exrheader_renderscene', bpy.data.filepath)
    params.SetString('exrheader_user', getpass.getuser())
    params.SetString('exrheader_statistics', statspath)

    integrator = shadergraph_utils.find_integrator_node(world)
    integrator_nm = 'PxrPathTracer'
    if integrator:
        integrator_nm = integrator.bl_label
    params.SetString('exrheader_integrator', integrator_nm)    
    
    params.SetFloatArray('exrheader_samples', [rm.hider_minSamples, rm.hider_maxSamples], 2)
    params.SetFloat('exrheader_pixelvariance', rm.ri_pixelVariance)
    params.SetString('exrheader_comment', rm.custom_metadata)

    if camera_name:
        if camera_name not in bpy.data.objects:
            return
        obj = bpy.data.objects[camera_name]     
        if obj.data.name not in bpy.data.cameras:
            return               
        cam = bpy.data.cameras[obj.data.name]

        if cam.dof.focus_object:
            dof_distance = (obj.location - cam.dof.focus_object.location).length
        else:
            dof_distance = cam.dof.focus_distance

        params.SetFloat('exrheader_fstop', cam.dof.aperture_fstop )
        params.SetFloat('exrheader_focaldistance', dof_distance )
        params.SetFloat('exrheader_focal', cam.lens )
        params.SetFloat('exrheader_haperture', cam.sensor_width )
        params.SetFloat('exrheader_vaperture', cam.sensor_height )       