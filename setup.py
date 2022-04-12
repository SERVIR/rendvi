import setuptools
from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(name='rendvi',
    version='0.0.1',
    description='Rapid Enhanced Normalaized Difference Vegetation Index (reNDVI)',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='http://github.com/servir/rendvi',
    packages=setuptools.find_packages(),
    author='Kel Markert',
    author_email='kel.markert@gmail.com',
    license='GPLv3',
    zip_safe=False,
    include_package_data=False,
    # entry_points={
    #     'console_scripts': [
    #         'rendvi = rendvi.cli:main',
    #     ],
    # },
    install_requires=["earthengine-api", "fire", "pandas"]
)
