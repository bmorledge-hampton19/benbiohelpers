from setuptools import setup, find_packages

with open("readme.md", "r") as fh:
    long_description = fh.read()

setup(
    name="mypyhelpers",
    version="0.1",
    description='Helper scripts for my use',
    long_description_content_type="text/markdown",
    url='https://github.com/bmorledge-hampton19/My_Python_Helpers',
    author='Ben Morledge-Hampton',
    author_email='b.morledge-hampton@wsu.edu',
    license='MIT',
    python_requires='>=3.7',
    packages=find_packages()
)