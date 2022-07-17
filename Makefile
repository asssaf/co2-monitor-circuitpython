PYLINT = pylint
PYLINTFLAGS = -rn

PYTHONFILES := $(wildcard src/*.py)

pylint: $(patsubst %.py,%.pylint,$(PYTHONFILES))

%.pylint:
	$(PYLINT) $(PYLINTFLAGS) $*.py


fetch-deps:
	@pip3 install -r requirements.txt -t lib

clean-deps:
	@rm -r lib

deploy: pylint
	@cp src/code.py /run/media/assaf/CIRCUITPY/
