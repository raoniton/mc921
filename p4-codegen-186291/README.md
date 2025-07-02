[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/y7pZPVU_)
# Code Generation

The objective of this assignment is transform the AST into MJIR and to run the MJIR with the interpreter.
Further instructions can be seen in the notebook provided with the assignment.

## Tasks

You should do the following tasks:

- [ ] Paste your implementation of the lexer in `mjc/mj_lexer.py`
- [ ] Paste your implementation of the parser in `mjc/mj_parser.py`
- [ ] Paste your implementation of the ast in `mjc/mj_ast.py`
- [ ] Paste your implementation of the semantic analysis in `mjc/mj_sema.py`
- [ ] Paste your implementation of the type system in `mjc/mj_type.py`
- [ ] Complete the implementation of the code generation in `mjc/mj_code.py`
- [ ] Complete the implementation of basic blocks in `mjc/mj_block.py`

Feel free to add modifications to files from previous projects such as `mj_type.py` or `mj_ast.py` to complement your solution.

## Requirements

Use Python 3.10 or a newer version.    
Required pip packages:
- sly, pytest, setuptools, graphviz, rich

## Install project

We recommend that you use a virtual environment to install the project and its dependencies
to avoid conflicts with the packages on your system. For example, you can install the package
and its dependencies using the following commands:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Docker
Alternatively you can also use Docker & Docker Compose (Docker Engine 19.03.0+) if you don't
want to setup a local environment.

## Running

After you have accepted this assignment on the course's Github Classroom page,
clone it to your machine.

You can run `mj_code.py` directly with python. For more information, run:

```sh
python3 mjc/mj_code.py -h
```

Or, if you installed the project in your environment, you can use the `mj-code`
command to run your code generator:

```sh
mj-code -h
```

You can use the inputs available inside
the `tests/in-out/` directory.

```sh
# Example running test 01
mj-code tests/in-out/t01.in
```

### Docker
If you're using the dockerized environment, to run `mj_code.py` directly you should run:
```sh
docker-compose run --rm test mjc/mj_code.py -h
``` 

```sh
# Example: running test 01
docker-compose run --rm test mjc/mj_code.py tests/in-out/t01.in
``` 

## Testing with Pytest

You can run all the tests in `tests/in-out/` automatically with `pytest`. For
that, you first need to make the source files visible to the tests. There are
two options:
- Install your project in editable mode using the `setup.py` file from the root
  of the repo
```sh
pip install -e .
```
- Or, add the repo folder to the PYTHONPATH environment variable with `setup.sh`
```sh
source setup.sh
```

### Docker
Running all tests in the dockerized environment:
```sh
# When installing Docker on linux, this is a way you can use compose.
# For Mac and Windows, don't forget the hyphen on docker-compose.
docker compose run --rm pytest
``` 

Then you should be able to run all the tests by running `pytest` at the root
of the repo.

### Linting and Formatting

This step is **optional**. Required pip packages:
- flake8, black, isort

You can install these packages along with the project in the virtual environment:
```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

You can lint your code with two `flake8` commands from the root of the repo:
```sh
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --exit-zero --max-line-length=120 --statistics
```

The first command shows errors that need to be fixed and will cause your
commit to fail. The second shows only warnings that are suggestions for
a good coding style.

To format the code, you can use `isort` to manage the imports and `black`
for the rest of the code. Run both from the root of the repo:
```sh
isort .
black .
```
## Grading

Your assignment will be evaluated in terms of:

- Correctness: your program returns correct results for the tests;

Whenever you push your changes to Github, Github Actions will lint and run your
implementation with `pytest` to test all the inputs in `tests/in-out`.
Your grade will be automatically determined by the autograding job.

To check your grade online:
- Go to the `Actions` tab in your repo
- Click on the latest commit
- Click on `build` on the left panel
    - This will show all the steps on the Autograding CI
- Click on the `Run tests with autograding` job and scroll to the bottom

You **must not** modify the test files.

**Note:** The automatic grading system expects your program's output to be
formatted correctly. For that reason, you should not add `print()` or any other
functions that write to `stdout`, otherwise, your assignment will not be graded
correctly.

**Note:** The final grade for this assignment will be determined by the lastest
commit before the deadline, and it will not use Github's autograding.
An internal grading script will be run instead to prevent cheating.

## Questions

If you have any doubts or run into problems, please contact the TAs.    
Happy coding! :smile: :keyboard:

## Contribute

Found a typo? Something is missing or broken? Have ideas for improvement? The
instructor and the TAs would love to hear from you!

## About

This repository is one of the assignments handed out to the students in the course
"MC921 - Compiler Construction" offered by the Institute of
Computing at Unicamp.
