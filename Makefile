.PHONY: hal test install clean
hal:
	$(MAKE) -C hal

install: hal
	$(MAKE) -C hal install

test:
	PYTHONPATH=. python3 -m unittest discover -s tests -v

clean:
	$(MAKE) -C hal clean
	rm -f smartcar/libsmartcar.so
