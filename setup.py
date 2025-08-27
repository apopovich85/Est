from setuptools import setup, find_packages

setup(
    name='project-estimates-manager',
    version='1.0.0',
    description='A Flask web application for managing project estimates',
    author='Your Name',
    author_email='your.email@example.com',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'Flask>=2.3.0',
        'Flask-SQLAlchemy>=3.0.0',
        'Flask-WTF>=1.1.0',
        'WTForms>=3.0.0',
        'python-dotenv>=1.0.0',
    ],
    python_requires='>=3.8',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Flask',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
)