#!/usr/bin/env python
"""Script to auto-generate our API docs.
"""
# stdlib imports
import os
import sys

# local imports
sys.path.append(os.path.abspath('sphinxext'))
from apigen import ApiDocWriter

#*****************************************************************************
if __name__ == '__main__':
    pjoin = os.path.join
    package = 'hexrd'
    outdir = pjoin('source','api','generated')
    docwriter = ApiDocWriter(package,rst_extension='.rst')
    # You have to escape the . here because . is a special char for regexps.
    # You must do make clean if you change this!
    docwriter.package_skip_patterns += [r'\.wx$',
                                        # Extensions are documented elsewhere.
                                        #r'\.extensions',
                                        #r'\.config\.profile',
                                        # These should be accessed via nbformat.current
                                        #r'\.nbformat\.v\d+',
                                        ]

    # The inputhook* modules often cause problems on import, such as trying to
    # load incompatible Qt bindings. It's easiest to leave them all out. The
    # main API is in the inputhook module, which is documented.
    docwriter.module_skip_patterns += [ r'\.new_detector',
                                        r'\.new_crystallography',
                                        #r'\.testing\.plugin',
                                        # This just prints a deprecation msg:
                                        #r'\.frontend$',
                                        # Deprecated:
                                        #r'\.core\.magics\.deprecated'
                                        # We document this manually.
                                        #r'\.utils\.py3compat',
                                        # These are exposed by nbformat.current
                                        #r'\.nbformat\.convert',
                                        #r'\.nbformat\.validator',
                                        # These are exposed in display
                                        #r'\.core\.display',
                                        #r'\.lib\.display',
                                        ]

    # These modules import functions and classes from other places to expose
    # them as part of the public API. They must have __all__ defined. The
    # non-API modules they import from should be excluded by the skip patterns
    # above.
    docwriter.names_from__all__.update({
        #'IPython.nbformat.current',
        #'IPython.display',
    })
    
    # Now, generate the outputs
    docwriter.write_api_docs(outdir)
    # Write index with .txt extension - we can include it, but Sphinx won't try
    # to compile it
    docwriter.write_index(outdir, 'gen.txt',
                          relative_to = pjoin('source','api')
                          )
    print ('%d files written' % len(docwriter.written_modules))

