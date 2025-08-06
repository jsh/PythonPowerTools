# PythonPowerTools

These tools are ports of the BSD utilities from the
PerlPowerTools (PPT) project, started by Tom Christiansen in February, 1999,
and currently maintained by brian d foy.

The Perl sources are drawn from the [PPT GitHub repository](https://github.com/briandfoy/PerlPowerTools.git) .
Default license for each tool is Perl's Artistic License 2.0, which can be found in LICENSE.md.

The steward for this license is the Perl and Raku Foundation.
I've copied the license from [this URL](https://www.perlfoundation.org/artistic-license-20.html),
adding markdown to the title and subheads by hand to make it look a little nicer.

At brian's suggestion, I've adopted this license for the project as a whole.
If any individual tool has a different license, it is specified in the source of that tool.


## TODO

* I'm going to try to create a first draft of each tool through a direct conversion by an AI assistant.
Will that work? Who knows.

  ***If you try to use a Python version of one of the tools, assume it's completely untested.***

* I'll have to add tests.

The PPT repository testing directory, `PPT/t` only lists individual tests for 25 of the 125 tools in `PPT/bin`,
so test-driven-development (TDD) is impractical.

I have no plan to add tests until I have created drafts of all the tools.

   *Caveat emptor.*

* pyproject.toml needs to be augmented to add package dependencies for a few utilities.

* I need to enhance `bin/port` and `bin/writeport` to work on Linux. Right now, they just work on my Mac.


## Notes

* First cuts were all done with Google Gemini 2.5 Pro, starting with the tool with the fewest lines, `rot13`,
and proceding to the one with the most, `ching`.

* The tools used for the conversion, `port` and `writeport` can be found in `bin/`.

I've only put the code into `python/<toolname>.py`,
but Gemini typically generated a summary before the code and discussion of how the code worked afterwards.
To see either, just convert the code yourself!

* Many utilities are no longer very useful. 

The utility `asa` interprets ASA/FORTRAN carriage-controls, which is only useful to folks who work in an institution that still uses FORTRAN,
such as the National Center for Atmospheric Research (NCAR).

For the rest of us, `asa` is historically interesting. It offers a glimpse into the history of computing: what used to be important enough to write utilities around.

* Some PPT utilities are really Perl-specific. A few of these have been converted into Python analogues.
Others like `PPT/bin/awk` and `PPT/bin/find` don't convert at all, because they depend on Perl.
`awk` is a front-end for `a2p`, and find is a front end for `find2perl`.
Python implementations of either are possible, but need to be done as an independent effort.
