#PiicoDev TMP117 Temp Sensor   - Code Library: https://core-electronics.com.au/guides/raspberry-pi-pico/piicodev-precision-temperature-sensor-tmp117-quickstart-guide-for-rpi-pico/
#WS2812B Addressable LED Strip - Code Library: https://github.com/shanno88/raspberry_Pi_Pico_WS2812B
#OLED LCD 128x128 ST7735       - Code Library: https://github.com/shadowframe/lcd-st7735

import array, time, utime, framebuf, rp2, random, math
from time import sleep, sleep_ms
from machine import Pin, I2C, SPI
from PiicoDev_TMP117 import PiicoDev_TMP117
from PiicoDev_Unified import sleep_ms # cross-platform compatible sleep function
from ST7735 import TFT, TFTColor
from sysfont import sysfont

#Temp Sensor TMP117
i2c = I2C(0, scl = Pin(09), sda = Pin(08), freq=200000)
tempSensor = PiicoDev_TMP117() # initialise the sensor

#OLED LCD 128x128 ST7735
# SCK = 02 , MOSI = 03 , DC = 00 , RST = 07 , CS = 01 
spi = SPI(0, baudrate=20000000, polarity=0, phase=0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
tft=TFT(spi,00,15,01)
tft.initr()
tft.rgb(False)
tft.fill(TFT.BLACK)

#ST7735 LCD Backlight Pin (Using a Pin for 3.3v for LED/BL)
lcdbl = Pin(14, Pin.IN, Pin.PULL_UP)
lcdbl.value(1)

#LCD Orientation, 0 = Portrait, 1 = Landscape [Options: 0,1,2,3]
tft.rotation(1)

# Configure the number of WS2812 LEDs.
NUM_STRIP = 1
NUM_LEDS = 24
TTL_LEDS = NUM_STRIP * NUM_LEDS
PIN_NUM = 27
#Brightness Range 0.1 - 1.0 
brightness = 0.1
brtdsp = 0
speed = 0.1

#Brightness Adjust
brightup = Pin(16, Pin.IN, Pin.PULL_UP)
brightdw = Pin(17, Pin.IN, Pin.PULL_UP)
brightup.value(1)
brightdw.value(1)

@rp2.asm_pio(sideset_init=rp2.PIO.OUT_LOW, out_shiftdir=rp2.PIO.SHIFT_LEFT, autopull=True, pull_thresh=24)
def ws2812():
    T1 = 2
    T2 = 5
    T3 = 3
    wrap_target()
    label("bitloop")
    out(x, 1)               .side(0)    [T3 - 1]
    jmp(not_x, "do_zero")   .side(1)    [T1 - 1]
    jmp("bitloop")          .side(1)    [T2 - 1]
    label("do_zero")
    nop()                   .side(0)    [T2 - 1]
    wrap()


# Create the StateMachine with the ws2812 program, outputting on pin
sm = rp2.StateMachine(0, ws2812, freq=8_000_000, sideset_base=Pin(PIN_NUM))

# Start the StateMachine, it will wait for data on its FIFO.
sm.active(1)

# Display a pattern on the LEDs via an array of LED RGB values.
ar = array.array("I", [0 for _ in range(TTL_LEDS)])

##################################################################################
#BMP Image Display Code

imagefile = "logo.bmp"
imgx = 00
imgy = 00

def image():
    f=open((imagefile), 'rb')
    if f.read(2) == b'BM':  #header
        dummy = f.read(8) #file size(4), creator bytes(4)
        offset = int.from_bytes(f.read(4), 'little')
        hdrsize = int.from_bytes(f.read(4), 'little')
        width = int.from_bytes(f.read(4), 'little')
        height = int.from_bytes(f.read(4), 'little')
        if int.from_bytes(f.read(2), 'little') == 1: #planes must be 1
            depth = int.from_bytes(f.read(2), 'little')
            if depth == 24 and int.from_bytes(f.read(4), 'little') == 0:#compress method == uncompressed
                rowsize = (width * 3 + 3) & ~3
                if height < 0:
                    height = -height
                    flip = False
                else:
                    flip = True
                w, h = width, height
                if w > 128: w = 128
                if h > 128: h = 128
                tft._setwindowloc(((imgx),(imgy)),(w - 1,h - 1))
                for row in range(h):
                    if flip:
                        pos = offset + (height - 1 - row) * rowsize
                    else:
                        pos = offset + row * rowsize
                    if f.tell() != pos:
                        dummy = f.seek(pos)
                    for col in range(w):
                        bgr = f.read(3)
                        tft._pushcolor(TFTColor(bgr[2],bgr[1],bgr[0]))

##########################################################################
#WS2812B Functions
                        
def pixels_show():
    dimmer_ar = array.array("I", [0 for _ in range(TTL_LEDS)])
    for i,c in enumerate(ar):
        r = int(((c >> 8) & 0xFF) * brightness)
        g = int(((c >> 16) & 0xFF) * brightness)
        b = int((c & 0xFF) * brightness)
        dimmer_ar[i] = (g<<16) + (r<<8) + b
    sm.put(dimmer_ar, 8)
    time.sleep_ms(10)

def pixels_set(i, color):
    ar[i] = (color[1]<<16) + (color[0]<<8) + color[2]

def pixels_fill(color):
    for i in range(len(ar)):
        pixels_set(i, color)

def color_chase(color, wait):
    for i in range(TTL_LEDS):
        pixels_set(i, color)
        time.sleep(wait)
        pixels_show()
    time.sleep(0.2)
        
def clear_led():
    for i in range(len(ar)):
        pixels_set(i, BLACK)
        
BLACK = (0, 0, 0)
RED = (255, 0, 0)
YELLOW = (255, 150, 0)
GREEN = (0, 255, 0)
CYAN = (0, 255, 255)
BLUE = (0, 0, 255)
PURPLE = (180, 0, 255)
WHITE = (255, 255, 255)
COLORS = (BLACK, RED, YELLOW, GREEN, CYAN, BLUE, PURPLE, WHITE)        
        
##################################################################################
#Variables

tempcfmt = 0
cooltemp1 = 0
cooltemp2 = 0
nortemp1 = 0
nortemp2 = 0
warmtemp1 = 0
warmtemp2 = 0
color = TFT.BLACK
linecolor = TFT.CYAN
read1sttemp = 0
read2ndtemp = 0

clear_led()

tempC = tempSensor.readTempC()
read1sttemp = '{:.1f}'.format(tempC)
read2ndtemp = '{:.1f}'.format(tempC)

def zzz():
    sleep(1)

##################################################################################
#Main Code by Luke

while True:
    
    if brightness >= 1.0:
        brightness = 1.0
    if brightness <= 0.1:
        brightness = 0.1
    
    #Brightness Up Button        
    if brightup.value() == 0:
        print(' ')
        print('BRIGHT UP PUSHED')
        if brightness == 1.0:
            print("Maximum Brightness")
            brightness == 1.0
        else:
            brightness = brightness + 0.1
            print("Brightness Increased To: " + str(brightness))
            brtdsp = '{:.1f}'.format(brightness)
            tft.fillrect((0, 34), (128, 96), color)
            tft.text((16,36), "Brightness Level:", TFT.WHITE, sysfont, 1)
            tft.vline((20, 46), 22, linecolor)
            tft.vline((105, 46), 22, linecolor)
            tft.hline((20, 46), 85, linecolor)
            tft.hline((20, 67), 85, linecolor)
            tft.text((24, 50), str(brtdsp) + "/1.0", TFT.PURPLE, sysfont, 2)
            pixels_show()
            zzz()
            tft.fillrect((23, 49), (80, 17), color)
            tft.fillrect((0, 35), (128, 10), color)
    
    #Brightness Down Button            
    if brightdw.value() == 0:
        print(' ')
        print('BRIGHT DOWN PUSHED')
        if brightness == 0.1:
            print("Minimum Brightness")
            brightness == 0.1
        else:
            brightness = brightness - 0.1
            print("Brightness Decreased To: " + str(brightness))
            brtdsp = '{:.1f}'.format(brightness)
            tft.fillrect((0, 34), (128, 96), color)
            tft.text((16,36), "Brightness Level:", TFT.WHITE, sysfont, 1)
            tft.vline((20, 46), 22, linecolor)
            tft.vline((105, 46), 22, linecolor)
            tft.hline((20, 46), 85, linecolor)
            tft.hline((20, 67), 85, linecolor)
            tft.text((24, 50), str(brtdsp) + "/1.0", TFT.PURPLE, sysfont, 2)
            pixels_show()
            zzz()
            tft.fillrect((23, 49), (80, 17), color)
            tft.fillrect((0, 35), (128, 10), color)

    #Refresh the Temp box when it changes
    if read1sttemp == read2ndtemp:
        pass
    else:
        print("Temp has changed to " + str(read2ndtemp))
        #             X   Y     W   H
        tft.fillrect((23, 49), (80, 17), color)
        
    #Read The Temprature 1st time
    tempC = tempSensor.readTempC() # Celsius
    read1sttemp = '{:.1f}'.format(tempC)
      
    #Change RGB LED Strip depending on Temp
    
    #Hot (Over 30 Degrees)
    if tempC >= 30.0000:
        image()
        pixels_fill(RED)
        pixels_show()
        tft.text((24,36), "Current Temp.", TFT.WHITE, sysfont, 1)
        tft.vline((20, 46), 22, linecolor)
        tft.vline((105, 46), 22, linecolor)
        tft.hline((20, 46), 85, linecolor)
        tft.hline((20, 67), 85, linecolor)
        tft.text((30, 50), str(read2ndtemp) + " C", TFT.RED, sysfont, 2)
        tft.text((0, 72), " Temp. Controls LEDs", TFT.WHITE, sysfont, 1)
        tft.text((0, 82), " COLD= 00-10 Degrees", TFT.BLUE, sysfont, 1)
        tft.text((0, 92), " COOL= 10-18 Degrees", TFT.CYAN, sysfont, 1)
        tft.text((0, 102), " FINE= 18-25 Degrees", TFT.GREEN, sysfont, 1)
        tft.text((0, 112), " WARM= 25-30 Degrees", TFT.YELLOW, sysfont, 1)
        tft.text((0, 122), "  HOT= 30+ Degrees", TFT.RED, sysfont, 1)
        
    #This is used to set a Temp Range 25-30 Degrees
    if tempC >= 25.0000:
        warmtemp1 = 1
    else:
        warmtemp1 = 0
    
    if tempC <= 29.9999:
        warmtemp2 = 1
    else:
        warmtemp2 = 0
        
    #Warm (25-30 Degrees)
    if warmtemp1 == 1 and warmtemp2 == 1:
        image()
        pixels_fill(YELLOW)
        pixels_show()
        tft.text((24,36), "Current Temp.", TFT.WHITE, sysfont, 1)
        tft.vline((20, 46), 22, linecolor)
        tft.vline((105, 46), 22, linecolor)
        tft.hline((20, 46), 85, linecolor)
        tft.hline((20, 67), 85, linecolor)
        tft.text((30, 50), str(read2ndtemp) + " C", TFT.YELLOW, sysfont, 2)
        tft.text((0, 72), " Temp. Controls LEDs", TFT.WHITE, sysfont, 1)
        tft.text((0, 82), " COLD= 00-10 Degrees", TFT.BLUE, sysfont, 1)
        tft.text((0, 92), " COOL= 10-18 Degrees", TFT.CYAN, sysfont, 1)
        tft.text((0, 102), " FINE= 18-25 Degrees", TFT.GREEN, sysfont, 1)
        tft.text((0, 112), " WARM= 25-30 Degrees", TFT.YELLOW, sysfont, 1)
        tft.text((0, 122), "  HOT= 30+ Degrees", TFT.RED, sysfont, 1)
    
    #This is used to set a Temp Range 19-30 Degrees
    if tempC >= 18.0000:
        nortemp1 = 1
    else:
        nortemp1 = 0
    
    if tempC <= 24.9999:
        nortemp2 = 1
    else:
        nortemp2 = 0
    
    #Normal (When 19 - 25 Degrees)
    if nortemp1 == 1 and nortemp2 == 1:
        image()
        pixels_fill(GREEN)
        pixels_show()
        tft.text((24,36), "Current Temp.", TFT.WHITE, sysfont, 1)
        tft.vline((20, 46), 22, linecolor)
        tft.vline((105, 46), 22, linecolor)
        tft.hline((20, 46), 85, linecolor)
        tft.hline((20, 67), 85, linecolor)
        tft.text((30, 50), str(read2ndtemp) + " C", TFT.GREEN, sysfont, 2)
        tft.text((0, 72), " Temp. Controls LEDs", TFT.WHITE, sysfont, 1)
        tft.text((0, 82), " COLD= 00-10 Degrees", TFT.BLUE, sysfont, 1)
        tft.text((0, 92), " COOL= 10-18 Degrees", TFT.CYAN, sysfont, 1)
        tft.text((0, 102), " FINE= 18-25 Degrees", TFT.GREEN, sysfont, 1)
        tft.text((0, 112), " WARM= 25-30 Degrees", TFT.YELLOW, sysfont, 1)
        tft.text((0, 122), "  HOT= 30+ Degrees", TFT.RED, sysfont, 1)
        
    #This is used to set a Temp Range 10-18 Degrees
    if tempC >= 10.0000:
        cooltemp1 = 1
    else:
        cooltemp1 = 0
    
    if tempC <= 17.9999:
        cooltemp2 = 1
    else:
        cooltemp2 = 0
        
    #Cool (10-18 Degrees)
    if cooltemp1 == 1 and cooltemp2 == 1:
        image()
        pixels_fill(CYAN)
        pixels_show()
        tft.text((24,36), "Current Temp.", TFT.WHITE, sysfont, 1)
        tft.vline((20, 46), 22, linecolor)
        tft.vline((105, 46), 22, linecolor)
        tft.hline((20, 46), 85, linecolor)
        tft.hline((20, 67), 85, linecolor)
        tft.text((30, 50), str(read2ndtemp) + " C", TFT.CYAN, sysfont, 2)
        tft.text((0, 72), " Temp. Controls LEDs", TFT.WHITE, sysfont, 1)
        tft.text((0, 82), " COLD= 00-10 Degrees", TFT.BLUE, sysfont, 1)
        tft.text((0, 92), " COOL= 10-18 Degrees", TFT.CYAN, sysfont, 1)
        tft.text((0, 102), " FINE= 18-25 Degrees", TFT.GREEN, sysfont, 1)
        tft.text((0, 112), " WARM= 25-30 Degrees", TFT.YELLOW, sysfont, 1)
        tft.text((0, 122), "  HOT= 30+ Degrees", TFT.RED, sysfont, 1)
    
    #Cold (When under 10 Degrees)
    if tempC <= 10.0000:
        image()
        pixels_fill(BLUE)
        pixels_show()
        tft.text((24,36), "Current Temp.", TFT.WHITE, sysfont, 1)
        tft.vline((20, 46), 22, linecolor)
        tft.vline((105, 46), 22, linecolor)
        tft.hline((20, 46), 85, linecolor)
        tft.hline((20, 67), 85, linecolor)
        tft.text((30, 50), str(read2ndtemp) + " C", TFT.BLUE, sysfont, 2)
        tft.text((0, 72), " Temp. Controls LEDs", TFT.WHITE, sysfont, 1)
        tft.text((0, 82), " COLD= 00-10 Degrees", TFT.BLUE, sysfont, 1)
        tft.text((0, 92), " COOL= 10-18 Degrees", TFT.CYAN, sysfont, 1)
        tft.text((0, 102), " FINE= 18-25 Degrees", TFT.GREEN, sysfont, 1)
        tft.text((0, 112), " WARM= 25-30 Degrees", TFT.YELLOW, sysfont, 1)
        tft.text((0, 122), "  HOT= 30+ Degrees", TFT.RED, sysfont, 1)
    
    #Read The Temprature 2nd time
    tempC = tempSensor.readTempC() # Celsius
    read2ndtemp = '{:.1f}'.format(tempC)   