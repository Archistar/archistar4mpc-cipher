## MPyC

To run the scripts, you only need a recent version of Python and MPyC installed.

Ciphers can be run directly. Appending `-M n` will run the script with `n` parties:

`python3 chacha20bin.py -M 3`

The `operations.py` script will run benchmarks of basic operations and output csv-files.

## MP-SPDZ

To run the scripts, you need MP-SPDZ installed; especially, you need to `make shamir-party.x`.

You can either copy the scripts to `Programs/Source` in your MP-SPDZ directory, then compile them like this:

`./compile.py lowmc`

And then run them like this:

`Scripts/shamir.sh lowmc`

Or you can follow the instructions [here](https://github.com/data61/MP-SPDZ#compiling-and-running-programs-from-external-directories).
