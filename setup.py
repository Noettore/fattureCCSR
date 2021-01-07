import setuptools

with open('README.md', 'r', encoding='utf-8') as readme:
    long_description = readme.read()

setuptools.setup(
    name='fatture_ccsr',
    version='0.0.1',
    author='Ettore Dreucci',
    author_email='ettore.dreucci@gmail.com',
    description='Utility to download or convert CCSR invoices to TeamSystem\'s TRAF2000 record',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/Noettore/fattureSanRossore',
    packages=setuptools.find_packages(),
    install_requires=[
        'wxPython',
        'requests',
        'Unidecode',
        'requests_ntlm',
        'openpyxl',
        'PyPDF2',
    ],
    include_package_data=True,
    license='MIT',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
