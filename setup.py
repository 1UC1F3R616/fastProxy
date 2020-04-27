from distutils.core import setup
setup(
  name = 'fastProxy',      
  packages = ['fastProxy'],  
  version = '0.1.2',      
  license='MIT',        
  description = 'Async application to get Free Working Proxies quickly',  
  author = '1UC1F3R616',                  
  author_email = 'kushchoudhary8@gmail.com',      
  url = 'https://github.com/1UC1F3R616/fastProxy',   
  download_url = 'https://github.com/1UC1F3R616/fastProxy/archive/v_01.2.tar.gz',   
  keywords = ['proxy', 'free', 'Asynchronous', 'Threaded', 'Python3'],  
  install_requires=[           
          'bs4',
          'requests',
          'fire',
      ],
  classifiers=[
    'Development Status :: 5 - Production/Stable',      # Chose either "3 - Alpha", "4 - Beta" or "5 - Production/Stable" as the current state of your package
    'Intended Audience :: Developers',     
    'Topic :: Software Development :: Build Tools',
    'License :: OSI Approved :: MIT License',   
    'Programming Language :: Python :: 3',      
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
  ],
)