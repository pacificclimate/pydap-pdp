from setuptools import setup, find_packages
import sys, os

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
NEWS = open(os.path.join(here, 'NEWS.txt')).read()


__version__ = '3.2.4'

install_requires = [
    'Numpy',
    'requests',
    'Webob',
    'simplejson'
]

docs_extras = [
    'Sphinx',
    'Pygments',
]

tests_require = [
    'WebTest',
]

testing_extras = tests_require + [
    'nose',
    'coverage',
    'virtualenv', # for scaffolding tests
]


setup(name='pydap_pdp',
    version=__version__,
    description="An implementation of the Data Access Protocol.",
    long_description=README + '\n\n' + NEWS,
    classifiers=[
      # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    ],
    keywords='opendap dods dap science data',
    author='Roberto De Almeida',
    author_email='roberto@dealmeida.net',
    url='http://pydap.org/',
    license='MIT',
    packages=find_packages('src'),
    package_dir = {'': 'src'},
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    extras_require = {
        'testing': testing_extras,
        'docs': docs_extras,
    },
    tests_require = tests_require,
    test_suite="pydap.tests",
    entry_points="""
        [pydap.response]
        das = pydap.responses.das:DASResponse
        dds = pydap.responses.dds:DDSResponse
        dods = pydap.responses.dods:DODSResponse
        asc = pydap.responses.ascii:ASCIIResponse
        ascii = pydap.responses.ascii:ASCIIResponse
        csv = pydap.responses.ascii:ASCIIResponse
        info = pydap.responses.info:InfoResponse

        [pydap.function]
        bounds = pydap.wsgi.functions:bounds
        mean = pydap.wsgi.functions:mean

        [console_scripts]
        pydap = pydap.wsgi.app:main
        dods = pydap.handlers.dap:dump
    """,
)
