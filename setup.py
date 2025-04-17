from setuptools import setup, find_packages

setup(
    name="health-tracking",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "fitbit",
        "pandas",
        "google-auth",
        "google-auth-oauthlib",
        "google-api-python-client",
    ],
    python_requires=">=3.9",
    scripts=[
        "bin/fitbit-data.py",
        "bin/sheets-upload.py",
    ],
)
