# Much of this was stolen from
# https://github.com/xolox/python-humanfriendly/blob/master/Makefile


publish:
	git push origin && git push --tags origin
	$(MAKE) clean
	pip install --quiet twine wheel
	python setup.py sdist bdist_wheel
	twine upload dist/*
	$(MAKE) clean

clean:
	rm -Rf *.egg .cache .coverage .tox build dist docs/build htmlcov
	find . -depth -type d -name __pycache__ -exec rm -Rf {} \;
	find . -type f -name '*.pyc' -delete


.PHONY: default install reset check test tox readme docs publish clean
