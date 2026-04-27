from setuptools import setup, find_packages

setup(
    name="dizi-helper",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "typer>=0.9.0",
        "rich>=13.0.0",
        "chinese-calendar>=1.8.0",
        "python-dateutil>=2.8.2",
        "python-dotenv>=1.0.0",
        "wcwidth>=0.2.13",
    ],
    entry_points={
        "console_scripts": [
            "dizi=src.cli:app",
        ],
    },
    author="mtt",
    description="竹笛课程管理 + 缴费提醒 + 统计助手",
    python_requires=">=3.10",
)
