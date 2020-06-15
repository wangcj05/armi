"""
Helpers for sphinx documentation.

Can be used by armi docs or docs of anything else that
can import armi.
"""
import sys
import inspect
from io import StringIO
import datetime
import os
import subprocess
import shutil

from docutils.parsers.rst import Directive, directives
from docutils import nodes, statemachine

APIDOC_DIR = ".apidocs"


def create_figure(path, caption=None, align=None, alt=None, width=None):
    """
    This method is available within ``.. exec::``. It allows someone to create a figure with a
    caption.
    """
    rst = [".. figure:: {}".format(path)]
    if align:
        rst += ["    :align: {}".format(align)]
    if alt:
        rst += ["    :alt: {}".format(alt)]
    if width:
        rst += ["    :width: {}".format(width)]
    if caption:
        rst += [""]
    if caption:
        rst += ["    {}".format(caption)]
    return rst


def create_table(rst_table, caption=None, align=None, widths=None, width=None):
    """
    This method is available within ``.. exec::``. It allows someone to create a table with a
    caption.

    The ``rst_table``
    """
    try:
        rst = [".. table:: {}".format(caption or "")]
        if align:
            rst += ["    :align: {}".format(align)]
        if width:
            rst += ["    :width: {}".format(width)]
        if widths:
            rst += ["    :widths: {}".format(widths)]
        rst += [""]
        rst += ["    " + line for line in rst_table.split("\n")]
        return "\n".join(rst)
    except:
        raise Exception("crap, crap crap!")


class ExecDirective(Directive):
    """Execute the specified python code and insert the output into the document.

    The code is used as the body of a method, and must return a ``str``. The string result is
    interpreted as reStructuredText.
    """

    has_content = True

    def run(self):
        try:
            code = inspect.cleandoc(
                """
            def usermethod():
                {}
            """
            ).format("\n    ".join(self.content))
            exec(code)
            result = locals()["usermethod"]()

            if result is None:
                raise Exception(
                    "Return value needed! The body of your `.. exec::` is used as a "
                    "function call that must return a value."
                )

            para = nodes.container()
            # tab_width = self.options.get('tab-width', self.state.document.settings.tab_width)
            lines = statemachine.StringList(result.split("\n"))
            self.state.nested_parse(lines, self.content_offset, para)
            return [para]
        except Exception as e:
            docname = self.state.document.settings.env.docname
            return [
                nodes.error(
                    None,
                    nodes.paragraph(
                        text="Unable to execute python code at {}:{} ... {}".format(
                            docname, self.lineno, datetime.datetime.now()
                        )
                    ),
                    nodes.paragraph(text=str(e)),
                    nodes.literal_block(text=str(code)),
                )
            ]


class PyReverse(Directive):
    """Runs pyreverse to generate UML for specified module name and options.

    The directive accepts the same arguments as pyreverse, except you should not specify
    ``--project`` or ``-o`` (output format). These are automatically specified.

    If you pass ``-c`` to this, the figure generated is forced to be the className.png
    like ``BurnMatrix.png``. For .gitignore purposes, this is a pain. Thus, we
    auto-prefix ALL images generated by this directive with ``pyrev_``.
    """

    has_content = True
    required_arguments = 1
    optional_arguments = 50
    option_spec = {
        "alt": directives.unchanged,
        "height": directives.length_or_percentage_or_unitless,
        "width": directives.length_or_percentage_or_unitless,
        "align": lambda arg: directives.choice(arg, ("left", "right", "center")),
        "filename": directives.unchanged,
    }

    def run(self):
        stdStreams = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = StringIO(), StringIO()
        try:
            args = list(self.arguments)
            args.append("--project")
            args.append(f"{args[0]}")
            args.append("-opng")

            # cannot use "pylint.pyreverse.main.Run" because it calls `sys.exit`. why?
            fig_name = self.options.get("filename", "classes_{}.png".format(args[0]))
            command = [sys.executable, "-m", "pylint.pyreverse.main"]
            print("Running {}".format(command + args))
            subprocess.check_call(command + args)

            try:
                os.remove(os.path.join(APIDOC_DIR, fig_name))
            except:
                pass

            shutil.move(fig_name, APIDOC_DIR)
            # add .gitignore helper prefix
            shutil.move(
                os.path.join(APIDOC_DIR, fig_name),
                os.path.join(APIDOC_DIR, f"pyr_{fig_name}"),
            )
            new_content = [f".. figure:: /{APIDOC_DIR}/pyr_{fig_name}"]

            # assume we don't need the packages_, and delete.
            try:
                os.remove("packages_{}.png".format(args[0]))
            except:
                pass

            # pass the other args through (figure args like align)
            for opt, val in self.options.items():
                if opt in ("filename",):
                    continue
                new_content.append("    :{}: {}\n".format(opt, val))

            new_content.append("\n")

            for line in self.content:
                new_content.append("    " + line)

            para = nodes.container()
            # tab_width = self.options.get('tab-width', self.state.document.settings.tab_width)
            lines = statemachine.StringList(new_content)
            self.state.nested_parse(lines, self.content_offset, para)
            return [para]
        except Exception as e:
            docname = self.state.document.settings.env.docname
            return [
                nodes.error(
                    None,
                    nodes.paragraph(
                        text="Unable to generate figure from {}:{} with command {} ... {}".format(
                            docname, self.lineno, command, datetime.datetime.now()
                        )
                    ),
                    nodes.paragraph(text=str(e)),
                    nodes.literal_block(text=str(sys.stdout.getvalue())),
                    nodes.literal_block(text=str(sys.stderr.getvalue())),
                )
            ]
        finally:
            sys.stdout, sys.stderr = stdStreams
