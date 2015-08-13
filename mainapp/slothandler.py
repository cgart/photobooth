
from kivy.animation import Animation


class SlotHandler:
        
	# ------------------------------------------------------------------
	def __init__(self, slotWidget):
        for widget in slotWidget.walk():
            print("{} -> {}".format(widget, widget.id))
            
        
