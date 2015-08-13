#!/usr/bin/python

import glob
from random import randint
from os.path import join, dirname
import piggyphoto
import time
import datetime
from functools import partial

from kivy.config import Config

# settings of the window
#Config.set('graphics', 'fullscreen', '0')
Config.set('graphics', 'width', '1800')
Config.set('graphics', 'height', '960')

captureFilePath = "captures/"
capturePreviewFile = "preview.jpg"

from kivy.app import App
from kivy.logger import Logger
from kivy.uix.scatter import Scatter
from kivy.uix.widget import Widget
from kivy.properties import StringProperty
from kivy.properties import NumericProperty
from kivy.clock import Clock
from kivy.uix.image import Image
from kivy.uix.image import AsyncImage
from kivy.properties import ObjectProperty
from kivy.loader import Loader
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Rectangle
from kivy.core.window import Window
from kivy.animation import Animation

import mainapp

# initialize camera<
##C.leave_locked()

# ----------------------------------------------------------------------
# Preview widget - showing the current preview picture
# ----------------------------------------------------------------------
class Preview(Widget):
	
	camera = None
	preview_image = ObjectProperty()
	image = Image(source = capturePreviewFile)
			
	# ------------------------------------------------------------------
	def setCamera(self, camera):
		self.camera = camera
		if camera != None:
			self.camera.capture_preview(capturePreviewFile)
		pass
			
	# ------------------------------------------------------------------
	def onNewFrame(self, proxyImage):
		self.preview_image.texture = proxyImage.image.texture
		pass
		
	# ------------------------------------------------------------------
	def updateFrame(self, dt):
		if self.camera != None:
			self.camera.capture_preview(capturePreviewFile)
		self.image.reload()
		self.preview_image.texture = self.image.texture
			
		pass

# ----------------------------------------------------------------------
# Widget animating a number in the center of the screen
# ----------------------------------------------------------------------
class CounterNum(Widget):
	
	label = ObjectProperty(None)
	rect = None
	texture_size = None
	label_texture = ObjectProperty(None)
	
	def __init__(self, num, **kwargs):
		super(CounterNum, self).__init__(**kwargs)
		
		# generate texture containing the desired label
		self.label = CoreLabel(text=str(num), font_size=500, color=(1,1,1,1))
		self.label.refresh()		
		self.texture_size = list(self.label.texture.size)
		self.label_texture = self.label.texture
		
		pass
		
	def animate(self):
		
		# animate widget
		size_old = self.texture_size
		size_new = (size_old[0] * 1.5, size_old[1] * 1.5)
		pos = self.pos
		anim = Animation(size=size_new, pos=(pos[0] - (size_new[0] - size_old[0])/2, pos[1] - (size_new[1] - size_old[1])/2), duration=0.25)
		anim.start(self)

		pass
		
		
# ----------------------------------------------------------------------
# Picture captured with camera
# ----------------------------------------------------------------------
class Picture(Scatter):
	
	#source = StringProperty(None)
	image = Image()
	alpha = NumericProperty()
	onLoadCallback = None
		
	def __init__(self, filename=None, onload=None, **kwargs):
		super(Picture, self).__init__(**kwargs)
		self.alpha = 0
		self.loadImage(filename, onload)

	def loadImage(self, filename, onload = None):
		if filename != None:
			print "Load image: " + filename
			proxyImage = Loader.image(filename)
			proxyImage.bind(on_load=self._image_loaded)
			self.onLoadCallback = onload
		
	def _image_loaded(self, proxyImage):
		if proxyImage.image.texture:
			self.image.texture = proxyImage.image.texture 
			anim = Animation(alpha=1, duration=0.2)
			anim.start(self)
			if self.onLoadCallback != None:
				self.onLoadCallback()

# ----------------------------------------------------------------------
# All slots of captured images are handled by this class
# ----------------------------------------------------------------------
class CapturedSlots(Scatter):
	
	pictureList = []
	currentIdx = 0
	layout = ObjectProperty(None)
			
	# prefill all slots with already taken images in chronological order
	def preloadSlots(self):
		
		# find all files
		files = glob.glob(captureFilePath + '/*.jpg')
		files = sorted(files)

		# for each child of type picture load image
		for child in self.layout.children:
			if type(child) is Picture:
				self.pictureList.append(child)
				
		# update all slots
		if len(files) > 0:			
			for pic in self.pictureList:				
				filename = files[-1]
				self.populateNextSlot(filename)
				if len(files) > 1:
					files.pop()
	
	# update image in the next slot - if all slots are full, then start from beginning		
	def populateNextSlot(self, filename):
		self.currentIdx = (self.currentIdx + 1) % len(self.pictureList)
		self.pictureList[self.currentIdx].loadImage(filename)
		
		
#				child.loadImage(filename)
#				files.pop()
				
	pass
	
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
class WhiteBillboard(Widget):
		
	alpha = NumericProperty()
	
	def __init__(self, **kwargs):
		super(WhiteBillboard, self).__init__(**kwargs)
		self.alpha = 0
			
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
class CaptureApp(App):
	    
	keyboard = None
	camera = None
	whiteBillboard = None
	previewImage = None
	slotImages = None
	
	# ------------------------------------------------------------------
	def __init__(self, **kwargs):
		super(CaptureApp, self).__init__(**kwargs)
		self.keyboard = Window.request_keyboard(self.onKeyboardClosed, self)
		self.keyboard.bind(on_key_down = self.onKeyDown)

		
		#self.camera = piggyphoto.camera()
		pass
					
	# ------------------------------------------------------------------
	def onKeyboardClosed(self):
		pass
		
	# ------------------------------------------------------------------
	def onKeyDown(self, keyboard, keycode, text, modifiers):
		print keycode
		if keycode[0] == 32:
			self.runCounter()
		pass		
		
	# ------------------------------------------------------------------
	def showCounter(self, N, old_label):
		
		# remove old number 
		if old_label != None:
			self.root.remove_widget(old_label)
		
		# we reached the 0, hence start picture taking
		if N == 0:
			self.captureImage()
			return
			
		# add counter label	
		label = CounterNum(N)
		label.animate()
		self.root.add_widget(label)		
		N = N-1
		if N >= 0:
			Clock.schedule_once(lambda dt: self.showCounter(N, label), 1.0)
			
	# ------------------------------------------------------------------
	def runCounter(self):
		self.showCounter(3, None)		
			
	# ------------------------------------------------------------------
	def captureImage(self):
		
		# show a flash on the screen in parallel to the capture process
		def _fadeIn():
			anim = Animation(alpha=1, duration=0.075)
			anim.start(self.whiteBillboard)
			
		def _fadeOut():
			anim = Animation(alpha=0,  duration=0.1)
			anim.start(self.whiteBillboard)
		
		Clock.schedule_once(lambda dt: _fadeIn(), 0.1)
		#Clock.schedule_once(lambda dt: _fadeOut, 0.125)
		
		# captue the actual image
		def _capture(dt):
			
			timestamp = time.time()
			st = datetime.datetime.fromtimestamp(timestamp).strftime('%H_%M_%S')		
			
			if self.camera == None:
				st = "test"
				
			filename = captureFilePath + st + ".jpg"
			print "capture image: " + filename
			
			if self.camera != None:
				self.camera.capture_image(filename)
			
			picture = Picture(filename, _fadeOut)
			self.root.add_widget(picture)		

		Clock.schedule_once(_capture,0.03)
		
		pass
		
	# ------------------------------------------------------------------
	def build(self):
		root = self.root
	
		self.previewImage = root.ids.camera_image
		self.whiteBillboard = root.ids.white_overlay
		self.slotImages = root.ids.picture_slots
		
		self.previewImage.setCamera(self.camera)	
		self.slotImages.preloadSlots()
		
		Clock.schedule_interval(self.previewImage.updateFrame, 1.0 / 10.0)
		pass

		
# ------------------------------------------------------------------
if __name__ == '__main__':	
	CaptureApp().run()
