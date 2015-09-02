#!/usr/bin/python

import glob
from random import randint
from os.path import join, dirname
import piggyphoto
import time
import datetime
from functools import partial
from random import randrange, uniform
from threading import Thread, Lock
import numpy as np


import kivy
kivy.require('1.9.1')

from kivy.config import Config

# settings of the window
#Config.set('graphics', 'fullscreen', '0')
#Config.set('graphics', 'width', '800')
#Config.set('graphics', 'height', '960')
Config.set('graphics', 'fbo', 'hardware')
#Config.set('graphics', 'fullscreen', '1')
Config.set('graphics', 'show_cursor', '0')

captureFilePath = "captures/"
capturePreviewFile = "preview.jpg"

from kivy.app import App
from kivy.logger import Logger
from kivy.uix.scatter import Scatter
from kivy.uix.widget import Widget
from kivy.properties import StringProperty
from kivy.properties import NumericProperty
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.uix.image import Image
#from kivy.uix.image import AsyncImage
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import ListProperty, ObjectProperty
from kivy.loader import Loader
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Rectangle, BorderImage
from kivy.graphics.texture import Texture
from kivy.core.window import Window
from kivy.animation import Animation
#from kivy.graphics import Color, Rectangle, Canvas, ClearBuffers, ClearColor
from kivy.graphics.fbo import Fbo
from kivy.graphics.transformation import Matrix
from kivy.graphics.shader import *
from kivy.graphics.opengl import *
from kivy.graphics import *
from kivy.cache import Cache

import mainapp

# Raspberry GPIO
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BOARD)
KEY_PIN = 40

class EKeyState:
	PRESSED = 'pressed'
	RELEASED = 'released'
	
keyState = EKeyState.RELEASED
GPIO.setup(KEY_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP) 

# initialize camera<
##C.leave_locked()


class FboFloatLayout(Widget):

	texture = ObjectProperty(None, allownone=True)
	vertices = ListProperty([])
	
	fbo = None
	tmp_fbo = None 
	
	def __init__(self, **kwargs):
		
		self.canvas = Canvas()
		
		with self.canvas:
			self.fbo = Fbo(size=self.size)
			
		super(FboFloatLayout, self).__init__(**kwargs)

	# --
	# preload FBO with background texture
	def initFbo(self):
		
		with self.fbo:
			ClearColor(0,0,0,0)
			ClearBuffers()
			Rectangle(source = 'data/background.jpg', size=self.size, pos=self.pos)

		self.texture = self.fbo.texture
				
	# --
	# add the content of the widget to the FBO
	# this will literally render the widget into the texture
	def render_widget(self, widget):

		# create an FBO to render the widget to
		self.tmp_fbo = Fbo(size = self.size)
		self.tmp_fbo.add(ClearColor(0,0,0,0))
		self.tmp_fbo.add(ClearBuffers())
		self.tmp_fbo.add(widget.canvas)
		self.tmp_fbo.draw()

		# render a rectangle in the main fbo containing the content from the widget
		with self.fbo:
			Color(1,1,1,1)
			Rectangle(texture=self.tmp_fbo.texture, size=self.tmp_fbo.size)
					
	#def add_widget(self, *largs):
		# trick to attach graphics instruction to fbo instead of canvas
	#	canvas = self.canvas
	#	self.canvas = self.fbo
	#	ret = super(FboFloatLayout, self).add_widget(*largs)
	#	self.canvas = canvas
		
		# remove widget after next frame, this makes sure that 
		# we do not use the widget for more than one frame
		#Clock.schedule_once(lambda dt: self.remove_widget(*largs))

	#	return ret

	#def remove_widget(self, *largs):
	#	canvas = self.canvas
	#	self.canvas = self.fbo
	#	super(FboFloatLayout, self).remove_widget(*largs)
	#	self.canvas = canvas

	def on_size(self, instance, value):
		self.size = value 
		
		self.fbo.size = value
		
		#self.fbo_rect.size = value
		#self.fbo_background.size = value
		#self.fbo_rect.texture = self.fbo.texture
		
		# setup simple quad mesh to be rendered
		# the quad is used for actual resizing
		self.vertices = []
		self.vertices.extend([0,0,0,0])
		self.vertices.extend([0,self.height,0,1])
		self.vertices.extend([self.width,self.height,1,1])
		self.vertices.extend([self.width,0,1,0])

		#self.updateFbo()		
		self.initFbo()
		
	#def on_pos(self, instance, value):
		#self.fbo_rect.pos = value
		#self.fbo_background.pos = value
	#	pass
		
	#def on_texture(self, instance, value):
		#self.texture = value
	#	pass
		
	#def on_alpha(self, instance, value):
	#	self.fbo_color.rgba = (1, 1, 1, value)
        
# ----------------------------------------------------------------------
# Preview widget - showing the current preview picture
# ----------------------------------------------------------------------
class Preview(Widget):
	
	camera = None
	preview_image = ObjectProperty()
	image = Image(source = capturePreviewFile)
	alpha = NumericProperty()
			
	def __init__(self, **kwargs):
		super(Preview, self).__init__(**kwargs)
		self.alpha = 0
		
	# ------------------------------------------------------------------
	def setCamera(self, camera):
		self.camera = camera
		self.alpha = 0
		if camera != None:
			self.camera.capture_preview(capturePreviewFile)
		pass
			
	# ------------------------------------------------------------------
	def onNewFrame(self, proxyImage):
		self.preview_image.texture = proxyImage.image.texture
		pass
		
	# ------------------------------------------------------------------
	def updateFrame(self):
		
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
	
	img_texture = ObjectProperty()
	alpha = NumericProperty()
	onLoadCallback = None
	filename = None
	
	vertices = ListProperty([])
	
	fbo_texture = ObjectProperty(None)
	fbo = None

	border_image = None
	keep_aspect = True
	
	aspectRatio = 1.0

	# --
	def __init__(self, filename=None, onload=None, **kwargs):
		
		self.canvas = Canvas()
		
		with self.canvas:
			self.fbo = Fbo(size=(512,512))
			self.fbo.add_reload_observer(self.updateFbo)
			
		self.border_image = CoreImage('data/shadow32.png')
		self.img_texture = Texture.create(size=(128,128), colorfmt="rgba")		
				
		self.alpha = 0		
		self.fbo_texture = self.fbo.texture
		
		super(Picture, self).__init__(**kwargs)		
		
		self.loadImage(filename, onload)
		

	# --
	def updateFbo(self):
			
		with self.fbo:
			ClearColor(0, 0, 0, 0)
			ClearBuffers()
			Color(1,1,1,1)
			BorderImage(texture=self.border_image.texture, border=(36,36,36,36), size = (self.fbo.size[0], self.fbo.size[1]), pos=(0,0))
			Rectangle(texture=self.img_texture, size=(self.fbo.size[0]-72, self.fbo.size[1]-72), pos=(36,36))
							
		self.fbo_texture = self.fbo.texture
		
		pass

	# --
	def on_size(self, instance, value):

		# change the underlying size property
		newAspectRatio = float(value[1]) / float(value[0])
		
		if self.keep_aspect:
			value[1] = value[0] * self.aspectRatio
			newAspectRatio = self.aspectRatio
						
		self.size = value
		
		# setup simple quad mesh to be rendered
		# the quad is used for actual resizing
		self.vertices = []
		self.vertices.extend([0,0,0,0])
		self.vertices.extend([0,self.height,0,1])
		self.vertices.extend([self.width,self.height,1,1])
		self.vertices.extend([self.width,0,1,0])

		
		# if the aspect ratio of the underlying FBO is not the same as the aspect
		# ratio of the new size, then change the size of the FBO
		fboAspectRatio = float(self.fbo.size[1]) / float(self.fbo.size[0])
		
		if abs(fboAspectRatio - newAspectRatio) > 0.1:
			fboSize = (self.fbo.size[0], self.fbo.size[1] * newAspectRatio)
			self.fbo.size = fboSize
			self.updateFbo()
			
		pass

	# --
	def loadImage(self, filename, onload = None):
		self.filename = filename
		if filename != None:
			self.onLoadCallback = onload
				
			proxyImage = Loader.image(filename)
					
			# this is totally stupid behaviour of Kivy
			# the docs suggest to bind proxy image's on_load method to a callback
			# to indicate when image is loaded. However, when image is already
			# in the cache the callback won't be called. My first thought was
			# that it was a threading issue, because the bindind might have happened
			# after the callback was initiated, but it seems that indeed the method is just not called.
			if proxyImage.loaded == False:
				proxyImage.bind(on_load=self._image_loaded)
			else:
				self._image_loaded(proxyImage)

	# --
	# All used memory except of the FBO texture is released. The image
	# can still be used, however, properties could not be changed
	def releaseMemory(self):
		
		self.img_texture = False
		self.border_image = False
		self.fbo_texture = Texture.create(size=(2,2), colorfmt="rgba")
				
		# clear up cache
		Cache.remove('kv.image')
		Cache.remove('kv.texture')
		Cache.remove('kv.loader')
			
		pass
		
	# --
	def _image_loaded(self, proxyImage):
		
		if proxyImage.image.texture:
			self.img_texture = proxyImage.image.texture
			self.aspectRatio = float(proxyImage.image.height) / float(proxyImage.image.width)
			self.updateFbo()
			
			anim = Animation(alpha=1, duration=0.2)
			anim.start(self)
			
			if self.onLoadCallback != None:
				self.onLoadCallback(self)

# ----------------------------------------------------------------------
# All slots of captured images are handled by this class
# ----------------------------------------------------------------------
class CapturedSlots(Widget):

	alpha = NumericProperty()
	pictureList = []
	currentIdx = 0
	layout = ObjectProperty(None)
	cells = None
	num_x = 16
	num_y = 9
	cell_w = 0
	cell_h = 0
	img_w = 640
	img_h = 640 / 1.777
	mutex = Lock()
	root = None 
	
	def __init__(self, **kwargs):
		super(CapturedSlots, self).__init__(**kwargs)
		self.alpha = 1.0
		
	# prefill all slots with already taken images in chronological order
	def preloadSlots(self):
		
		# setup cell matrix with possible possible picture spots
		self.cells = [[None] * self.num_x for i in range(self.num_y)]
		self.cell_w = self.width / self.num_x
		self.cell_h = self.height / self.num_y
		
		# find all files
		files = glob.glob(captureFilePath + '/*.jpg')
		files = sorted(files)

		#print('screen: %dx%d' % (self.width, self.height))
		#print('cells: %dx%d' % (self.cell_w, self.cell_h))
		
		# for each child of type picture load image
		for child in self.layout.children:
			if type(child) is Picture:
				self.pictureList.append(child)
				
		# update all slots
		if len(files) > 0:			
			#for pic in self.pictureList:
			for filename in files:
				self.populateNextSlot(filename)
	
	# update image in the next slot - if all slots are full, then start from beginning		
	def populateNextSlot(self, filename):

		# add new picture spread randomly over the screen
		newpic = Picture()
		newpic.center_x = self.width/2
		newpic.center_y = self.height/2
		newpic.filename = filename 
		
		self.addExistingImage(newpic)

	# add a new image into a random slot.
	# the image will be animated from its current position and scale down
	# to the required by the slot
	def addExistingImage(self, picture, onImageRenderedInto = None):

		self.mutex.acquire()
		
		# find a random cell where we put the image into
		cell = (randint(0, self.num_x-1), randint(0, self.num_y-1))
		poscntr = ((cell[0] + 0.5) * self.cell_w, (cell[1] + 0.5) * self.cell_h)
		rot = uniform(-35,35)
		
		# remove any images in the cell
		if self.cells[cell[1]][cell[0]] != None:
			wdgt = self.cells[cell[1]][cell[0]]
			#self.layout.remove_widget(wdgt)
		
		# add image as widget into the main root first, because
		# we want to keep it animated for a while
		self.cells[cell[1]][cell[0]] = picture
		self.root.add_widget(picture)
		
		self.mutex.release()
		
		# start animation of the image to be positioned in the slot
		# when animation stops we burn the image into the FloatLayout
		def _animate(pic):
			anim = Animation(center_x=poscntr[0], center_y=poscntr[1], width = 800, rotation = randint(0,2) * 360 + rot, duration=1.7)
			anim.start(pic)

			# ensure that the widget 
			# make sure that we render the picture into the main layout only once 
			# and then remove the used texture - this ensures smaller memory footprint
			def _addImageToLayout(anim, pic, on_cmpl):
				self.root.remove_widget(pic)
				self.layout.render_widget(pic)
				
				Clock.schedule_once(lambda dt: pic.releaseMemory(), 1.)
				
				if on_cmpl != None:
					on_cmpl(anim, pic)
				
			anim.bind(on_complete = lambda a,w: _addImageToLayout(a,w,onImageRenderedInto))
			
			
		picture.loadImage(picture.filename, lambda pic: _animate(pic))
							
		pass
		
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
class EState:
	LOADING 	= 'loading'
	PREVIEW  	= 'preview'
	COUNTER  	= 'countdown'
	CAPTURING   = 'capture'
	INSPECTION	= 'inspect'
	SLIDESHOW	= 'slideshow'
	STOPSHOW    = 'stop slideshow'
	
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
class CaptureApp(App):
	    
	keyboard = None
	camera = None
	whiteBillboard = None
	previewImage = None
	slotImages = None
	state = EState.LOADING
	latestCapturedPicture = None

	# slideshow part
	slideShowAvailableFiles = []
	slideShowAvailableFileProbabilities = []
	slideShowCurrentPictures = []
	slideShowLastTimestamp = 0
	slideShowPictureSpeed = []
	
	# ------------------------------------------------------------------
	def __init__(self, **kwargs):
		super(CaptureApp, self).__init__(**kwargs)
		#self.keyboard = Window.request_keyboard(self.onKeyboardClosed, self)
		#self.keyboard.bind(on_key_down = self.onKeyDown)

		
		#self.camera = piggyphoto.camera()
		pass
					
	# ------------------------------------------------------------------
	def countDown(self, N, old_label, callback):
		
		# remove old number 
		if old_label != None:
			self.root.remove_widget(old_label)
		
		# we reached the 0, hence start picture taking
		if N == 0:
			callback()
			return
			
		# add counter label	
		label = CounterNum(N)
		label.animate()
		self.root.add_widget(label)		
		N = N-1
		if N >= 0:
			Clock.schedule_once(lambda dt: self.countDown(N, label, callback), 1.0)
						
	# ------------------------------------------------------------------
	# show a flash on the screen in parallel to the capture process
	def fadeIn(self, dt = 0.075, onComplete = None):
		anim = Animation(alpha=1, duration=dt)
		anim.start(self.whiteBillboard)
		if onComplete != None:
			anim.bind(on_complete = lambda a,w: onComplete())			
			
	def fadeOut(self, dt = 0.1, onComplete = None):
		anim = Animation(alpha=0,  duration=dt)
		anim.start(self.whiteBillboard)
		if onComplete != None:
			anim.bind(on_complete = lambda a,w: onComplete())			
			
	# ------------------------------------------------------------------
	def captureImageImpl(self, onLoadCallback):
		
							
		# captue the actual image
		def _capture():
			
			timestamp = time.time()
			st = datetime.datetime.fromtimestamp(timestamp).strftime('%H_%M_%S')		
			
			if self.camera == None:
				st = "test"
				
			filename = captureFilePath + st + ".jpg"
			print "capture image to " + filename
			
			if self.camera != None:
				self.camera.capture_image(filename)
				
			# load image and show it in the center
			picture = Picture(filename, onLoadCallback)
			picture.center_x = self.root.width / 2
			picture.center_y = self.root.height / 2
			
		def _disablePreview():
			self.previewImage.alpha = 0
			
		Clock.schedule_once(lambda dt: self.fadeIn(), 0.1)
		Clock.schedule_once(lambda dt: self.fadeOut(), 0.275)
		Clock.schedule_once(lambda dt: _disablePreview(), 0.175)
		Clock.schedule_once(lambda dt: _capture(),0.03)
		
		pass
		
		
		
	# ------------------------------------------------------------------
	def build(self):		
		
		self.previewImage = self.root.ids.camera_image
		self.previewImage.setCamera(self.camera)	
		
		self.whiteBillboard = self.root.ids.white_overlay
		self.slotImages = self.root.ids.picture_slots		
		self.slotImages.root = self.root 
		
		# todo - this should be better called after scene graph is created and not just after some amount of time
		Clock.schedule_once(lambda dt: self.preloadSlots(), 0.5)		 
		Clock.schedule_interval(lambda dt: self.checkGPIO(), 1./20.)
		
		pass


	# ------------------------------------------------------------------
	def checkGPIO(self):
		global keyState
		
		# no need to debounce, since this method is called every 100ms anyway
		# and storing the last state gives us a debouncing automagically
		if keyState == EKeyState.RELEASED and GPIO.input(KEY_PIN) == 0:
			keyState = EKeyState.PRESSED
			self.userEvent() #onKeyDown(None, (32,0), None, None)
		if keyState == EKeyState.PRESSED and GPIO.input(KEY_PIN) == 1:
			keyState = EKeyState.RELEASED
			
		pass
		
	# ------------------------------------------------------------------
	def onKeyboardClosed(self):
		pass
		
	# ------------------------------------------------------------------
	def onKeyDown(self, keyboard, keycode, text, modifiers):
		
		Cache.print_usage()
		
		if keycode[0] == 32:
			
			self.userEvent()
				
		pass		
		
		
	# ---------------------- State Machine -----------------------------
	
	# ------------------------------------------------------------------
	# User event, performs state transitions based on the current state
	# ------------------------------------------------------------------
	def userEvent(self):
				
		if self.state == EState.PREVIEW:
			self.runCounter()
		
		elif self.state == EState.INSPECTION:
			self.removeLatestImage()
			
		elif self.state == EState.SLIDESHOW:
			self.stopSlideShow()
			
		pass
	
	# ------------------------------------------------------------------
	# Animate latest captured image to the background
	# ------------------------------------------------------------------
	def removeLatestImage(self):
		
		if self.latestCapturedPicture != None:
			self.root.remove_widget(self.latestCapturedPicture)
			self.slotImages.addExistingImage(self.latestCapturedPicture, lambda anim,pic: self.startPreview())
			self.latestCapturedPicture = None

			# clear up cache
			Cache.remove('kv.image')
			Cache.remove('kv.texture')
			Cache.remove('kv.loader')
			
		pass
		
	# ------------------------------------------------------------------
	# Image was captured and we inspect it
	# ------------------------------------------------------------------
	def inspectImage(self, picture):

		self.state = EState.INSPECTION
		
		# make picture visible
		picture.size = (1000., 1000. * picture.aspectRatio)
		picture.center_x = self.root.width / 2
		picture.center_y = self.root.height / 2
		self.latestCapturedPicture = picture
		self.root.add_widget(picture)
			
		# animate image to the background - event
		Clock.schedule_once(lambda dt: self.removeLatestImage(), 3.0)
		
		pass
		
	# ------------------------------------------------------------------
	# Start counter for capture
	# ------------------------------------------------------------------
	def captureImage(self):
		
		self.state = EState.CAPTURING
		self.captureImageImpl(self.inspectImage)
		
		pass
		
	# ------------------------------------------------------------------
	# Start counter for capture
	# ------------------------------------------------------------------
	def runCounter(self):
		
		self.state = EState.COUNTER
		self.countDown(3, None, self.captureImage)		
			
		pass
		
	# ------------------------------------------------------------------
	# Show preview image from camera
	# ------------------------------------------------------------------
	def startPreview(self, doFadeIn = True):
		
		# update loop for the preview frame
		def _updatePreview():			
			self.previewImage.updateFrame()
			
			if self.state != EState.PREVIEW and self.state != EState.COUNTER:
				return False

			return True
			
		# set state and start frame updates
		def _setState():
			self.state = EState.PREVIEW
			Clock.schedule_interval(lambda dt: _updatePreview(), 1.0 / 10.0)
				
		if doFadeIn:
			anim = Animation(alpha=1.0, t='in_cubic', duration=1.0)
			anim.bind(on_complete = lambda a,w: _setState())
			anim.start(self.previewImage)
		else:
			_setState()
			
		Clock.schedule_once(lambda dt: self.startSlideShow(), 10.)
					
		pass
		
						
	# ------------------------------------------------------------------
	# Populate background with all available images
	# ------------------------------------------------------------------
	def preloadSlots(self):
		
		self.state = EState.LOADING		
		self.slotImages.preloadSlots()
		self.startPreview()
		
		pass
		
		
	# ------------------------------------------------------------------
	# Start slide show
	# ------------------------------------------------------------------
	def startSlideShow(self):
			
		# we can only start from a preview state
		if self.state == EState.PREVIEW:
			self.state = EState.SLIDESHOW
										
			# just because python does not support assignments in the ambda
			def _setAlpha():
				self.slotImages.alpha = 0
				self.previewImage.alpha = 0
				
				# add all picture widgets
				for (pic,speed) in self.slideShowCurrentPictures:
					self.root.add_widget(pic,1)
					
				Clock.schedule_interval(self.updateSlideShow, 1.0 / 60.0)
				pass
			
			Clock.schedule_once(lambda dt: self.fadeIn(0.4, _setAlpha), 0.05)
			Clock.schedule_once(lambda dt: self.fadeOut(0.2), 0.8)

			# read in all available images and assign to them uniform probabilities
			self.slideShowAvailableFiles = glob.glob(captureFilePath + "*.jpg")
			self.slideShowAvailableFileProbabilities = [1.0 for i in xrange(len(self.slideShowAvailableFiles))]
			
		pass
		
	# ------------------------------------------------------------------
	# Stop slide show
	# ------------------------------------------------------------------
	def stopSlideShow(self):
				
		# slide show can only be stopped if we are in slideshow state	
		if self.state == EState.SLIDESHOW:
			
			self.state = EState.STOPSHOW
			
			# just because python does not support assignments in the lambda
			def _setAlpha():
				self.slotImages.alpha = 1
				self.previewImage.alpha = 1
				self.startPreview(False)
				
				# remove all picture widgets
				for (pic,speed) in self.slideShowCurrentPictures:
					self.root.remove_widget(pic)
									
				pass
				
			Clock.schedule_once(lambda dt: self.fadeIn(0.3, _setAlpha), 0.05)
			Clock.schedule_once(lambda dt: self.fadeOut(0.1), 0.35)
			
		pass
		
	# ------------------------------------------------------------------
	# Update slide show
	# ------------------------------------------------------------------
	def updateSlideShow(self, dtime):
		
		# do not continue with updates, if stop requested
		if self.state == EState.STOPSHOW:			
			return False

		# if enough time passed, since the last change of the image
		# then add a new image into the list of currently visible images
		currentTime = Clock.get_time()
		if currentTime > self.slideShowLastTimestamp:
			
			# select randomly a file from all available files
			# the selected files get it's probability reduced
			idx = np.random.choice(len(self.slideShowAvailableFiles), 1, self.slideShowAvailableFileProbabilities)
			self.slideShowAvailableFileProbabilities[idx] *= 0.75
			
			# create a new image from the selected file, this will be shown
			def _addImageStartScrolling(pic):
				width = randint(700, 1000)
				pic.keep_aspect = True
				pic.size = (width, width)
				pic.x = uniform(0, self.root.width) - width / 2
				pic.y = -pic.size[1]
				pic.rotation = uniform(-25,25)
				self.slideShowCurrentPictures.append( (pic, uniform(100,200)) )
				self.root.add_widget(pic,1)				
				
			pic = Picture(self.slideShowAvailableFiles[idx], _addImageStartScrolling)
			
			# repeat the process in X seconds
			self.slideShowLastTimestamp = currentTime + 3.0
			pass
								
		# all images which are currently available, are scrolled through the screen
		validPictures = []
		for (pic,speed) in self.slideShowCurrentPictures:
			pic.y += dtime * speed
			
			if pic.y < self.root.height:
				validPictures.append( (pic,speed) )
			else:
				
				def _removeImage(w):
					Cache.remove('kv.image')
					Cache.remove('kv.texture')
					Cache.remove('kv.loader')
					self.root.remove_widget(w)
					
				anim = Animation(alpha=0, duration=0.5)
				anim.bind(on_complete = lambda a,w: _removeImage(w))
				anim.start(pic)
				
		self.slideShowCurrentPictures = validPictures
		
		
		# continue updates
		return True
		
		pass
			
# ------------------------------------------------------------------
if __name__ == '__main__':	
	CaptureApp().run()
	GPIO.cleanup()
	
