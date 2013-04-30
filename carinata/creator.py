# coding: utf-8
"""Functions to create an AST of a unittest module"""
import ast

from carinata.utils import camelify, snakify


class InvalidSetupError(Exception):
    """Error caused when we select a bad parent node"""
    pass


def module(top_node, test_module, test_class):
    """Create an AST of a generated unittest module"""
    mod = ast.Module(body=[])

    # Import unittest (or specified test class) TestCase
    unittest_import = ast.ImportFrom(module=test_module, names=[
        ast.alias(name=test_class, asname=None)], level=0)
    mod.body.append(unittest_import)

    # Other top-level code
    code = ast.parse(top_node.code()).body
    mod.body.extend(code)

    return mod

def klass(node, test_class):
    """Create unittest class containing tests"""
    ancestor_names = [camelify(n.words) for n in node.ancestors()]
    class_name = ''.join(reversed(ancestor_names))
    cls = ast.ClassDef(name=class_name, body=[], decorator_list=[])
    base_class = ast.Name(id=test_class, ctx=ast.Load())

    cls.bases = [base_class]
    cls.body.extend(setup(node))
    cls.body.extend(tests(node))

    return cls

def setup(node):
    """Create setUp from ‘before’s and ‘let’s"""
    # Create a setUp function
    setup_func = setup_def()

    definitions = [setup_func]

    # Go though all setup functions above this node
    for i, setup_node in enumerate(node.setup()):
        func_name = snakify(setup_node.words)

        if setup_node.name == 'before':
            func_name += "_%d" % i
            setup_caller = before_call
        elif setup_node.name == 'let':
            setup_caller = let_call
        else:
            msg = "setup nodes must be called 'before' or 'let'"
            raise InvalidSetupError(msg)

        setup_definition = setup_def("_set_up_%s" % func_name)
        setup_code = ast.parse(setup_node.dedented_code()).body

        setup_definition.body.extend(setup_code)
        definitions.append(setup_definition)

        setup_call = setup_caller(func_name)
        setup_func.body.append(setup_call)

    return definitions

def setup_def(func_name="setUp"):
    """Create setup definition functions for setUp (and ‘_set_up_*’)"""
    setup_func = ast.FunctionDef(name=func_name)
    setup_func.body = []
    setup_func.decorator_list = []

    args = ast.arguments(vararg=None, kwarg=None, defaults=[])
    args.args = [ast.Name(id="self", ctx=ast.Param())]
    setup_func.args = args

    return setup_func

def before_call(func_name):
    """Create the call to ‘self._set_up_each_*’"""
    return ast.Expr(value=_set_up_call(func_name))

def let_call(func_name):
    """Create the call for ‘self.a = self._set_up_a()’"""
    target = ast.Attribute(value=ast.Name(id='self', ctx=ast.Load()),
            attr=func_name, ctx=ast.Store())
    return ast.Assign(targets=[target], value=_set_up_call(func_name))

def _set_up_call(func_name):
    """AST for function call with name ‘func_name’"""
    func = ast.Attribute(value=ast.Name(id='self', ctx=ast.Load()),
            attr="_set_up_%s" % func_name, ctx=ast.Load())
    return ast.Call(func=func, args=[], keywords=[],
            starargs=None, kwargs=None)

def tests(node):
    """Create a list of all test methods"""
    test_funcs = []
    for test in node.siblings():
        # Write the funtion line and the code
        func_name = "test_%s" % snakify(test.words)
        test_def = setup_def(func_name)
        test_code = ast.parse(test.dedented_code()).body
        test_def.body.extend(test_code)
        test_funcs.append(test_def)
    return test_funcs

def main_runner(test_module):
    """Create unittest.main(), protected by __name__ test"""
    name_test = ast.If(test=ast.Compare(
        left=ast.Name(id='__name__', ctx=ast.Load()),
        ops=[ast.Eq()],
        comparators=[ast.Str(s='__main__')]), orelse=[])
    main_runner_attr = ast.Attribute(
            value=ast.Name(id='unittest', ctx=ast.Load()),
            attr='main', ctx=ast.Load())
    main_runner_func = ast.Expr(value=ast.Call(func=main_runner_attr,
        args=[], keywords=[], starargs=None, kwargs=None))
    if test_module:
        name_test.body = [ast.Pass()]
    else:
        name_test.body = [main_runner_func]
    return name_test

