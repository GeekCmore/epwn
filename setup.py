from setuptools import setup, find_packages

setup(
    name="epwn",
    version="0.1.0",
    description="GLIBC版本管理和ELF补丁工具",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click>=8.0.0',
        'rich>=10.0.0',
        'requests>=2.25.0',
        'beautifulsoup4>=4.9.0',
    ],
    entry_points={
        'console_scripts': [
            'epwn=epwn.cli.main:cli',
        ],
    },
    python_requires='>=3.8',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'Programming Language :: Python :: 3.8',
    ],
) 