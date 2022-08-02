PYLINT = pylint
PYLINTFLAGS = -rn

PYTHONFILES := $(wildcard src/*.py)
LIB_FILES := adafruit_il0373.mpy adafruit_lc709203f.mpy adafruit_scd4x.mpy adafruit_ticks.mpy \
	neopixel.mpy adafruit_display_text/ asyncio/
LIB_PATHS := $(addprefix $(LIB_DIR)/,$(LIB_FILES))

pylint: $(patsubst %.py,%.pylint,$(PYTHONFILES))

%.pylint:
	$(PYLINT) $(PYLINTFLAGS) $*.py


fetch-deps:
	@pip3 install --upgrade -r requirements.txt -t lib

clean-deps:
	@rm -r lib

check-libs:
ifndef LIB_DIR
	$(error LIB_DIR is undefined)
endif

deploy-libs: check-libs
	cp -av $(LIB_PATHS) /run/media/$(USER)/CIRCUITPY/lib/

deploy: pylint
	install src/code.py /run/media/$(USER)/CIRCUITPY/

all: deploy

.PHONY: all fetch-deps clean-deps deploy pylint
