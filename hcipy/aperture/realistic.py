import numpy as np
from ..field import CartesianGrid, UnstructuredCoords, make_hexagonal_grid, Field
from .generic import *

def make_vlt_aperture():
	pass

def make_subaru_aperture():
	pass

def make_lbt_aperture():
	pass

def make_magellan_aperture(normalized=False, with_spiders=True):
	'''Make the Magellan aperture.

	Parameters
	----------
	normalized : boolean
		If this is True, the outer diameter will be scaled to 1. Otherwise, the
		diameter of the pupil will be 6.5 meters.
	with_spiders: boolean
		If this is False, the spiders will be left out.

	Returns
	-------
	Field generator
		The Magellan aperture.
	'''
	pupil_diameter = 6.5 #m
	spider_width1 = 0.75 * 0.0254 #m
	spider_width2 = 1.5 * 0.0254 #m
	central_obscuration_ratio = 0.29
	spider_offset = [0,0.34] #m

	if normalized:
		spider_width1 /= pupil_diameter
		spider_width2 /= pupil_diameter
		spider_offset = [x / pupil_diameter for x in spider_offset]
		pupil_diameter = 1.0

	spider_offset = np.array(spider_offset)

	mirror_edge1 = (pupil_diameter / (2 * np.sqrt(2)), pupil_diameter / (2 * np.sqrt(2)))
	mirror_edge2 = (-pupil_diameter / (2 * np.sqrt(2)), pupil_diameter / (2 * np.sqrt(2)))
	mirror_edge3 = (pupil_diameter / (2 * np.sqrt(2)), -pupil_diameter / (2 * np.sqrt(2)))
	mirror_edge4 = (-pupil_diameter / (2 * np.sqrt(2)), -pupil_diameter / (2 * np.sqrt(2)))

	obstructed_aperture = make_obstructed_circular_aperture(pupil_diameter, central_obscuration_ratio)

	if not with_spiders:
		return obstructed_aperture

	spider1 = make_spider(spider_offset, mirror_edge1, spider_width1)
	spider2 = make_spider(spider_offset, mirror_edge2, spider_width1)
	spider3 = make_spider(-spider_offset, mirror_edge3, spider_width2)
	spider4 = make_spider(-spider_offset, mirror_edge4, spider_width2)

	def func(grid):
		return obstructed_aperture(grid) * spider1(grid) * spider2(grid) * spider3(grid) * spider4(grid)
	return func

def make_keck_aperture():
	pass

def make_luvoir_a_aperture(gap_padding = 5, normalized=True, with_spiders=True, with_segment_gaps=True, segment_transmissions=1, header = False):
	'''Make the LUVOIR A aperture and Lyot Stop.

	This aperture changes frequently. This one is based on LUVOIR Apertures dimensions 
	from Matt Bolcar, LUVOIR lead engineer (as of 10 April 2019)
	Spiders and segment gaps can be included or excluded, and the transmission for each 
	of the segments can also be changed.

	Parameters
	----------
	gap_padding: float
		arbitratry padding of gap size to represent gaps on smaller arrays - effectively 
		makes the gaps larger and the segments smaller to preserve the same segment pitch 
	normalized : boolean
		If this is True, the outer diameter will be scaled to 1. Otherwise, the
		diameter of the pupil will be 15.0 meters.
	with_spiders : boolean
		Include the secondary mirror support structure in the aperture.
	with_segment_gaps : boolean
		Include the gaps between individual segments in the aperture.
	segment_transmissions : scalar or array_like
		The transmission for each of the segments. If this is a scalar, this transmission 
		will be used for all segments.
	
	Returns
	-------
	Field generator
		The LUVOIR A aperture.
	
	aperture_header: dictionary
		dictionary of keywords to build aperture fits header
	'''
	
	pupil_diameter = 15.0 #m actual circumscribed diameter, used for lam/D calculations other measurements normalized by this diameter
	actual_segment_flat_diameter = 1.2225 #m actual segment flat-to-flat diameter
	actual_segment_gap=0.006 #m actual gap size between segments
	spider_width=0.150 #m actual strut size
	lower_spider_angle = 12.7 #deg angle at which lower spiders are offset from vertical
	spid_start = 0.30657 #m spider starting point distance from center of aperture

	segment_gap =  actual_segment_gap * gap_padding #padding out the segmentation gaps so they are visible and not sub-pixel
	segment_flat_diameter = actual_segment_flat_diameter - (segment_gap - actual_segment_gap)
	segment_circum_diameter = 2 / np.sqrt(3) * segment_flat_diameter #segment circumscribed diameter
	
	num_rings = 6 #number of full rings of hexagons around central segment

	lower_spider_angle = 12.7 #deg spiders are upside-down 'Y' shaped; degree the lower two spiders are offset from vertical by this amount

	if not with_segment_gaps:
		segment_gap = 0

	aperture_header = {'TELESCOP':'LUVOIR A','D_CIRC': pupil_diameter, \
                   'SEG_F2F_D':actual_segment_flat_diameter,'SEG_GAP':actual_segment_gap, \
                   'STRUT_W':spider_width,'STRUT_AN':lower_spider_angle,'NORM':normalized, \
                   'SEG_TRAN':segment_transmissions,'GAP_PAD':gap_padding, 'STRUT_ST':spid_start, \
                   'PROV':'MBolcar ppt 20180815'}
	
	if normalized:
		segment_circum_diameter /= pupil_diameter
		actual_segment_flat_diameter /= pupil_diameter
		actual_segment_gap /= pupil_diameter
		spider_width /= pupil_diameter
		spid_start /= pupil_diameter
		pupil_diameter = 1.0

	segment_positions = make_hexagonal_grid(actual_segment_flat_diameter + actual_segment_gap, num_rings)
	segment_positions = segment_positions.subset(circular_aperture(pupil_diameter * 0.98)) #corner clipping
	segment_positions = segment_positions.subset(lambda grid: ~(circular_aperture(segment_circum_diameter)(grid) > 0))

	hexagon = hexagonal_aperture(segment_circum_diameter)
	def segment(grid):
		return hexagon(grid.rotated(np.pi/2))
	
	if with_spiders:
		spider1 = make_spider_infinite([0, 0], 90, spider_width)
		spider2 = make_spider_infinite([spid_start, 0], 270 - lower_spider_angle, spider_width)
		spider3 = make_spider_infinite([-spid_start, 0], 270 + lower_spider_angle, spider_width)

	segmented_aperture = make_segmented_aperture(segment, segment_positions, segment_transmissions)

	def func(grid):
		res = segmented_aperture(grid)

		if with_spiders:
			res *= spider1(grid) * spider2(grid) * spider3(grid)

		return Field(res, grid)
	
	
	if header:
		return func, aperture_header
	
	return func

def make_luvoir_a_lyot_stop(ls_id, ls_od, lyot_ref_diameter, spid_oversize=1, normalized=True, spiders=False, header = False):
	
	pupil_diameter=15.0 #m actual circumscribed diameter, used for lam/D calculations other measurements normalized by this diameter
	
	spider_width=0.150 #m actual strut size
	lower_spider_angle = 12.7 #deg angle at which lower spiders are offset from vertical
	spid_start = 0.30657 #m spider starting point offset from center of aperture
	
	
	outer_D = lyot_ref_diameter*ls_id
	inner_D = lyot_ref_diameter*ls_od
	pad_spid_width = spider_width * spid_oversize
	
	ls_header = {'TELESCOP':'LUVOIR A','D_CIRC': pupil_diameter, 'LS_ID':ls_id, \
	            'LS_OD':ls_od,'LS_REF_D':lyot_ref_diameter, 'NORM':normalized, 'STRUT_ST':spid_start}
	
	if spiders:
		ls_header['STRUT_W']  = spider_width
		ls_header['STRUT_AN'] = lower_spider_angle
		ls_header['STRUT_P']  = spid_oversize
	
	if normalized:
		outer_D /= pupil_diameter
		inner_D /= pupil_diameter
		pad_spid_width /= pupil_diameter
		spid_start /= pupil_diameter
	
	outer_diameter = circular_aperture(outer_D)
	central_obscuration = circular_aperture(inner_D)

	if spiders:
		spider1 = make_spider_infinite([0, 0], 90, pad_spid_width)
		spider2 = make_spider_infinite([spid_start,0], 270 - lower_spider_angle, pad_spid_width)
		spider3 = make_spider_infinite([-spid_start,0], 270 + lower_spider_angle, pad_spid_width)

	def aper(grid):
		tmp_result = (outer_diameter(grid) - central_obscuration(grid)) 
		if spiders:
			tmp_result *= spider1(grid) * spider2(grid) * spider3(grid)
		return tmp_result    
	
	if header:
		return aper, ls_header
		
	return aper

def make_hicat_aperture(normalized=False, with_spiders=True, with_segment_gaps=True, segment_transmissions=1):
	'''Make the HiCAT pupil mask.

	This function is a WIP. It should NOT be used for actual designs. Current pupil should be taken as
	representative only.

	Parameters
	----------
	normalized : boolean
		If this is True, the outer diameter will be scaled to 1. Otherwise, the
		diameter of the pupil will be 15.0 meters.
	with_spiders : boolean
		Include the secondary mirror support structure in the aperture.
	with_segment_gaps : boolean
		Include the gaps between individual segments in the aperture.
	segment_transmissions : scalar or array_like
		The transmission for each of the segments. If this is a scalar, this transmission will
		be used for all segments.

	Returns
	-------
	Field generator
		The HiCAT aperture.
	'''
	pupil_diameter = 0.019725 # m
	segment_circum_diameter = 2 / np.sqrt(3) * pupil_diameter / 7
	num_rings = 3
	segment_gap = 90e-6
	spider_width = 350e-6

	if not with_segment_gaps:
		segment_gap = 0

	if normalized:
		segment_circum_diameter /= pupil_diameter
		segment_gap /= pupil_diameter
		spider_width /= pupil_diameter
		pupil_diameter = 1.0

	segment_positions = make_hexagonal_grid(segment_circum_diameter / 2 * np.sqrt(3), num_rings)
	segment_positions = segment_positions.subset(lambda grid: ~(circular_aperture(segment_circum_diameter)(grid) > 0))

	hexagon = hexagonal_aperture(segment_circum_diameter - segment_gap)
	def segment(grid):
		return hexagon(grid.rotated(np.pi/2))

	segmented_aperture = make_segmented_aperture(segment, segment_positions, segment_transmissions)

	if with_spiders:
		spider1 = make_spider_infinite([0, 0], 60, spider_width)
		spider2 = make_spider_infinite([0, 0], 120, spider_width)
		spider3 = make_spider_infinite([0, 0], 240, spider_width)
		spider4 = make_spider_infinite([0, 0], 300, spider_width)

	def func(grid):
		res = segmented_aperture(grid)

		if with_spiders:
			res *= spider1(grid) * spider2(grid) * spider3(grid) * spider4(grid)

		return Field(res, grid)
	return func

def make_hicat_lyot_stop(normalized=False, with_spiders=True):
	'''Make the HiCAT Lyot stop.

	This function is a WIP. It should NOT be used for actual designs. Current Lyot stop should be taken as
	representative only.

	Parameters
	----------
	normalized : boolean
		If this is True, the outer diameter will be scaled to 1. Otherwise, the
		diameter of the pupil will be 15.0 meters.
	with_spiders : boolean
		Include the secondary mirror support structure in the aperture.

	Returns
	-------
	Field generator
		The HiCAT Lyot stop.
	'''
	pupil_diameter = 19.9e-3
	lyot_outer = 15.9e-3
	lyot_inner = 6.8e-3
	spider_width = 700e-6

	if normalized:
		lyot_inner /= pupil_diameter
		lyot_outer /= pupil_diameter
		spider_width /= pupil_diameter

	aperture = circular_aperture(lyot_outer)
	obscuration = circular_aperture(lyot_inner)

	if with_spiders:
		spider1 = make_spider_infinite([0, 0], 60, spider_width)
		spider2 = make_spider_infinite([0, 0], 120, spider_width)
		spider3 = make_spider_infinite([0, 0], 240, spider_width)
		spider4 = make_spider_infinite([0, 0], 300, spider_width)

	def func(grid):
		res = aperture(grid) - obscuration(grid)

		if with_spiders:
			res *= spider1(grid) * spider2(grid) * spider3(grid) * spider4(grid)

		return Field(res, grid)
	return func

def make_elt_aperture():
	pass
