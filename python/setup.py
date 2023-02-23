from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="benbiohelpers",
    version="1.2.2",
    description='Helper scripts for use in various bioinformatics projects',
    long_description_content_type="text/markdown",
    url='https://github.com/bmorledge-hampton19/benbiohelpers',
    author='Ben Morledge-Hampton',
    author_email='b.morledge-hampton@wsu.edu',
    license='MIT',
    python_requires='>=3.7',
    packages=find_packages(),
    package_data={"benbiohelpers": ["TkWrappers/test_tube.png"]}
)