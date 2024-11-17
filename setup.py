from distutils.core import setup
setup(
  name = 'fastProxy',
  packages = ['fastProxy'],
  version = '1.0.0',
  license='MIT',
  description = 'Fast and reliable proxy scraper with comprehensive validation and logging',
  author = '1UC1F3R616',
  author_email = 'kushchoudhary8@gmail.com',
  url = 'https://github.com/1UC1F3R616/fastProxy',
  download_url = 'https://github.com/1UC1F3R616/fastProxy/archive/v_1.0.0.tar.gz',
  keywords = ['proxy', 'free', 'threaded', 'python3', 'logging', 'validation'],
  install_requires=[
          'bs4',
          'requests',
          'fire',
          'pytest',
          'pytest-cov',
      ],
  classifiers=[
    'Development Status :: 5 - Production/Stable',      # Chose either "3 - Alpha", "4 - Beta" or "5 - Production/Stable" as the current state of your package
    'Intended Audience :: Developers',
    'Topic :: Software Development :: Build Tools',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Programming Language :: Python :: 3.10',
    'Programming Language :: Python :: 3.11',
    'Programming Language :: Python :: 3.12',
  ],
)
