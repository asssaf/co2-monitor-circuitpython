PYLINT = pylint
PYLINTFLAGS = -rn

PYTHONFILES := $(wildcard src/*.py)
LIB_DIR := $(HOME)/dev/adafruit/adafruit-circuitpython-bundle-7.x-mpy-20220715/lib
LIB_FILES := adafruit_il0373.mpy adafruit_scd4x.mpy neopixel.mpy
LIB_PATHS := $(addprefix $(LIB_DIR)/,$(LIB_FILES))

pylint: $(patsubst %.py,%.pylint,$(PYTHONFILES))

%.pylint:
	$(PYLINT) $(PYLINTFLAGS) $*.py


fetch-deps:
	@pip3 install --upgrade -r requirements.txt -t lib

clean-deps:
	@rm -r lib

deploy-libs:
	install $(LIB_PATHS) /run/media/$(USER)/CIRCUITPY/lib/

deploy: pylint
	install src/code.py /run/media/$(USER)/CIRCUITPY/

all: deploy

.PHONY: all fetch-deps clean-deps deploy pylint
