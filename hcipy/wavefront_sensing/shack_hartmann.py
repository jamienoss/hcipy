from .wavefront_sensor import WavefrontSensorOptics, WavefrontSensorEstimator
from ..optics import *
from ..field import *
from ..aperture import *
from ..propagation import FresnelPropagator
from ..multiprocessing import par_map

import numpy as np

class ShackHartmannWavefrontSensorOptics(WavefrontSensorOptics):
	def __init__(self, input_grid, micro_lens_array):
		# Make propagator
		sh_prop = FresnelPropagator(input_grid, micro_lens_array.focal_length)
		
		# Make optical system
		OpticalSystem.__init__(self, (micro_lens_array, sh_prop))
		self.mla_index = micro_lens_array.mla_index
		self.mla_grid = micro_lens_array.mla_grid
		self.micro_lens_array = micro_lens_array

class SquareShackHartmannWavefrontSensorOptics(ShackHartmannWavefrontSensorOptics):
	## Helper class to create a Shack-Hartmann WFS with square microlens array
	def __init__(self, input_grid, f_number, num_lenslets, pupil_diameter):
		lenslet_diameter = float(pupil_diameter) / num_lenslets
		x = np.arange(-pupil_diameter, pupil_diameter, lenslet_diameter)
		self.mla_grid = CartesianGrid(SeparatedCoords((x, x)))

		focal_length = f_number * lenslet_diameter
		self.micro_lens_array = MicroLensArray(input_grid, self.mla_grid, focal_length)
		
		ShackHartmannWavefrontSensorOptics.__init__(self, input_grid, self.micro_lens_array)

class ShackHartmannWavefrontSensorEstimator(WavefrontSensorEstimator):
	def __init__(self, mla_grid, mla_index):
		self.mla_grid = mla_grid
		self.mla_index = mla_index
		self.unique_indices = np.unique(self.mla_index)
		
	def estimate(self, images):
		image = images[0]
		
		def get_centroid(index):
			mask = self.mla_index == index

			subimage = image[mask]
			x = image.grid.x[mask]
			y = image.grid.y[mask]

			centroid_x = np.sum(subimage * x) / np.sum(subimage)
			centroid_y = np.sum(subimage * y) / np.sum(subimage)

			centroid = np.array((centroid_x, centroid_y)) - self.mla_grid[index]
			return centroid
		
		centroids = np.array(par_map(get_centroid, self.unique_indices, use_progressbar=False))

		return Field(centroids, self.mla_grid)