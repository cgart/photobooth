#!/usr/bin/python

from kivy.config import Config


# ----------------------------------------------------------------------
# Settings
# ----------------------------------------------------------------------

# Folder where all full-res captures from camera goes
captureFilePath = "/media/odroid/B5BD-FED7/photobooth/captures/"

# Folder with resized captures (smaller for faster loading)
captureSnapshotPath = "/media/odroid/B5BD-FED7/photobooth/snapshots/"

# Filename for the preview image from the camera to be updated
capturePreviewFile = "preview.jpg"

# Width of the snapshot files
captureSnapshowWidth = 600

# Maximal texture size of the pictures displayed on the screen
pictureMaxTexSize=(512,512)

# Width of the captued image, when previewing on the screen (height is chosen according to the aspect ratio)
inspectImageWidth = 1200

# Time for the camera shutter [sec]
cameraShutterLatency = 1.2

# Path to the Imagemagick's convert executable
convertCmd = "/usr/bin/convert"

# settings of the window
#Config.set('graphics', 'fullscreen', '0')
Config.set('graphics', 'width', '1920')
Config.set('graphics', 'height', '1080')
Config.set('graphics', 'fbo', 'hardware')
Config.set('graphics', 'fullscreen', '1')
Config.set('graphics', 'show_cursor', '0')
Config.set('graphics', 'borderless', '1')


# ----------------------------------------------------------------------
# Libraries
# ----------------------------------------------------------------------

# system librareis
import glob
from os.path import join, dirname
import piggyphoto
import time
import datetime
from threading import Thread, Lock
import numpy as np
import imp
from random import randrange, uniform, randint
from subprocess import call


# Kivy libraries
import kivy
kivy.require('1.9.1')
from kivy.app import App
from kivy.logger import Logger
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.cache import Cache


# Photobooth application
from mainapp.fbolayout import FboFloatLayout
from mainapp.preview import Preview
from mainapp.slothandler import CapturedSlots
from mainapp.picture import Picture
from mainapp.counter import CounterNum
from mainapp.helpers import WhiteBillboard



# Raspberry GPIO
HasRpiGPIO = False
try:
	imp.find_module('RPi')	
	import RPi.GPIO as GPIO
	GPIO.setmode(GPIO.BOARD)
	KEY_PIN = 40
	HasRpiGPIO = True
	GPIO.setup(KEY_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP) 
	
	print 'RaspberryPi GPIO library found'
except ImportError:
	pass



# ----------------------------------------------------------------------
class EKeyState:
	PRESSED = 'pressed'
	RELEASED = 'released'
				
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
	mutex = Lock()
	keyState = EKeyState.RELEASED

	# slideshow part
	slideShowAvailableFiles = []
	slideShowAvailableFileProbabilities = []
	slideShowCurrentPictures = []
	slideShowLastTimestamp = 0
	slideShowPictureSpeed = []
	
	# ------------------------------------------------------------------
	def __init__(self, **kwargs):
		super(CaptureApp, self).__init__(**kwargs)
		
		if HasRpiGPIO == False:
			self.keyboard = Window.request_keyboard(self.onKeyboardClosed, self)
			self.keyboard.bind(on_key_down = self.onKeyDown)

		
		try:
			self.camera = piggyphoto.camera()
		except:
			self.camera = None
			
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
	def build(self):		
		
		self.title = 'Photobooth'
		self.previewImage = self.root.ids.camera_image
		self.previewImage.setCamera(capturePreviewFile, self.camera)	
		
		self.whiteBillboard = self.root.ids.white_overlay
		self.slotImages = self.root.ids.picture_slots		
		self.slotImages.root = self.root 
		self.slotImages.setImageFilePath(captureSnapshotPath)
		self.slotImages.picMaxTexSize = pictureMaxTexSize
		
		# todo - this should be better called after scene graph is created and not just after some amount of time
		Clock.schedule_once(lambda dt: self.preloadSlots())
		
		if HasRpiGPIO == True:
			Clock.schedule_interval(lambda dt: self.checkGPIO(), 1./20.)
		
		pass


	# ------------------------------------------------------------------
	def checkGPIO(self):
		
		# no need to debounce, since this method is called every 100ms anyway
		# and storing the last state gives us a debouncing automagically
		if self.keyState == EKeyState.RELEASED and GPIO.input(KEY_PIN) == 0:
			self.keyState = EKeyState.PRESSED
			self.userEvent() #onKeyDown(None, (32,0), None, None)
		if self.keyState == EKeyState.PRESSED and GPIO.input(KEY_PIN) == 1:
			self.keyState = EKeyState.RELEASED
			
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
				
		self.mutex.acquire()
		
		# check if we can connect to the camera
		if self.camera == None:
			try:
				self.camera = piggyphoto.camera()
				self.previewImage.setCamera(capturePreviewFile, self.camera)	
			except:
				self.camera = None

		if self.state == EState.PREVIEW:
			self.mutex.release()
			self.runCounter()
		
		elif self.state == EState.INSPECTION:
			self.mutex.release()
			self.removeLatestImage()
			
		elif self.state == EState.SLIDESHOW:
			self.mutex.release()
			self.stopSlideShow()
			
		else:
			self.mutex.release()
			
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
		picture.size = (float(inspectImageWidth), float(inspectImageWidth) * picture.aspectRatio)
		picture.center_x = self.root.width / 2
		picture.center_y = self.root.height / 2
		self.latestCapturedPicture = picture
		self.root.add_widget(picture, 1)
			
		# animate image to the background - event
		Clock.schedule_once(lambda dt: self.removeLatestImage(), 3.0)
		
		pass
		
		
	# ------------------------------------------------------------------
	# capture the actual image to a file	
	# ------------------------------------------------------------------
	def captureImageThread(self, camera, onLoadCallback):

		# generate filename of the new file
		timestamp = time.time()
		st = datetime.datetime.fromtimestamp(timestamp).strftime('%Y%m%d_%H%M%S')					
		if camera == None: st = "test"			
		filename = captureFilePath + st + ".jpg"
		
		print "capture image to " + filename
		
		# capture file if camera is available
		if camera != None: camera.capture_image(filename)
				
		# generate a reduced version of the image in the snapshots folder
		filename_small = captureSnapshotPath + st + ".jpg"
		cmd = [convertCmd, '-geometry', str(captureSnapshowWidth) + 'x', filename, filename_small]
		print "resize image: " + str(cmd)
		call(cmd)
		
		# load image and show it in the center
		def _addCapturedImage():			
			picture = Picture(filename_small, onLoadCallback, pictureMaxTexSize)
			#picture.center_x = self.root.width / 2
			#picture.center_y = self.root.height / 2
			
		Clock.schedule_once(lambda dt: _addCapturedImage(), 0)
			
	# ------------------------------------------------------------------
	# Start counter for capture
	# ------------------------------------------------------------------
	def captureImage(self):

		self.mutex.acquire()
				
		self.state = EState.CAPTURING
		
		# disable preview images
		self.previewImage.disablePreview()
							
		# start a new thread with the actual capturing process
		Thread(target=self.captureImageThread, args=(self.camera,self.inspectImage,)).start()

		# start whiteout effect slightly later to fit to the shutter of the camera
		Clock.schedule_once(lambda dt: self.fadeIn(0.1, self.previewImage.hide()), cameraShutterLatency)
		Clock.schedule_once(lambda dt: self.fadeOut(), cameraShutterLatency + 0.2)
		
		self.mutex.release()
		
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
			self.mutex.acquire()
			
			self.previewImage.updateFrame()
			
			ret = True
			if self.state != EState.PREVIEW and self.state != EState.COUNTER:
				ret = False

			self.mutex.release()
			
			return ret
			
		# set state and start frame updates
		def _setState():
			self.mutex.acquire()
			
			self.state = EState.PREVIEW
			self.previewImage.show()
			self.previewImage.enablePreview()
			Clock.schedule_interval(lambda dt: _updatePreview(), 1.0 / 20.0)
			
			self.mutex.release()
				
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
		self.startPreview()
		Clock.schedule_once(lambda dt: self.slotImages.preloadSlots(), 1.0)
		
		pass
		
		
	# ------------------------------------------------------------------
	# Start slide show
	# ------------------------------------------------------------------
	def startSlideShow(self):
		
		self.mutex.acquire()
			
		# we can only start from a preview state
		if self.state == EState.PREVIEW:
										
			# read in all available images and assign to them uniform probabilities
			self.slideShowAvailableFiles = glob.glob(captureSnapshotPath + "*.jpg")
			self.slideShowAvailableFileProbabilities = [1.0 for i in xrange(len(self.slideShowAvailableFiles))]
			
			if len(self.slideShowAvailableFiles) == 0:
				self.mutex.release()
				return
				
			self.state = EState.SLIDESHOW
			
			# just because python does not support assignments in the ambda
			def _setAlpha():
				self.slotImages.alpha = 0
				self.previewImage.hide()
				self.previewImage.disablePreview()
				
				# add all picture widgets
				for (pic,speed) in self.slideShowCurrentPictures:
					self.root.add_widget(pic,1)
					
				Clock.schedule_interval(self.updateSlideShow, 1.0 / 40.0)
				pass
			
			Clock.schedule_once(lambda dt: self.fadeIn(0.4, _setAlpha), 0.05)
			Clock.schedule_once(lambda dt: self.fadeOut(0.2), 0.8)

			
		self.mutex.release()
		
		pass
		
	# ------------------------------------------------------------------
	# Stop slide show
	# ------------------------------------------------------------------
	def stopSlideShow(self):

		self.mutex.acquire()
						
		# slide show can only be stopped if we are in slideshow state	
		if self.state == EState.SLIDESHOW:
			
			self.state = EState.STOPSHOW
			
			# just because python does not support assignments in the lambda
			def _setAlpha():
				self.slotImages.alpha = 1
				#self.previewImage.show()
				self.startPreview(False)
				
				# remove all picture widgets
				for (pic,speed) in self.slideShowCurrentPictures:
					self.root.remove_widget(pic)
									
				pass
				
			Clock.schedule_once(lambda dt: self.fadeIn(0.3, _setAlpha), 0.05)
			Clock.schedule_once(lambda dt: self.fadeOut(0.1), 0.35)
	
		self.mutex.release()
				
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
				width = randint(float(self.root.width)/2.5, float(self.root.width)/1.5)
				pic.keep_aspect = True
				pic.size = (width, width)
				pic.x = uniform(-width/3., self.root.width - width + width/3.)
				pic.y = -pic.size[1]
				pic.rotation = uniform(-25,25)
				self.slideShowCurrentPictures.append( (pic, uniform(100,200)) )
				self.root.add_widget(pic,1)				
				
			pic = Picture(self.slideShowAvailableFiles[idx], _addImageStartScrolling, pictureMaxTexSize)
			
			# repeat the process in X seconds
			self.slideShowLastTimestamp = currentTime + 2.0
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
	
	if HasRpiGPIO == True:
		GPIO.cleanup()
	
