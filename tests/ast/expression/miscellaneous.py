#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  tests/ast/expression/miscellaneous.py
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are
#  met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following disclaimer
#    in the documentation and/or other materials provided with the
#    distribution.
#  * Neither the name of the project nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#  A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#  OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#  LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import datetime
import random
import string
import unittest

from .literal import context, trueish, falseish
import rule_engine.ast as ast
import rule_engine.engine as engine
import rule_engine.errors as errors

import dateutil.tz

__all__ = (
	'ContainsExpressionTests',
	'SymbolExpressionTests',
	'SymbolExpressionConversionTests',
	'TernaryExpressionTests',
	'UnaryExpressionTests'
)

class ContainsExpressionTests(unittest.TestCase):
	def test_ast_expression_contains(self):
		container = ast.LiteralExpressionBase.from_value(context, range(3))

		member = ast.FloatExpression(context, 1.0)
		contains = ast.ContainsExpression(context, member, container)
		self.assertTrue(contains.evaluate(None))
		self.assertIsInstance(contains.reduce(), ast.BooleanExpression)

		member = ast.FloatExpression(context, -1.0)
		contains = ast.ContainsExpression(context, member, container)
		self.assertFalse(contains.evaluate(None))
		self.assertIsInstance(contains.reduce(), ast.BooleanExpression)

		container = ast.StringExpression(context, 'Rule Engine')

		member = ast.StringExpression(context, ' ')
		self.assertTrue(ast.ContainsExpression(context, member, container).evaluate(None))

		member = ast.StringExpression(context, 'x')
		self.assertFalse(ast.ContainsExpression(context, member, container).evaluate(None))

	def test_ast_expression_contains_error(self):
		container = ast.StringExpression(context, 'Rule Engine')
		member = ast.FloatExpression(context, 1.0)
		with self.assertRaises(errors.EvaluationError):
			ast.ContainsExpression(context, member, container).evaluate(None)

		container = ast.FloatExpression(context, 1.0)
		with self.assertRaises(errors.EvaluationError):
			ast.ContainsExpression(context, member, container).evaluate(None)

class SymbolExpressionTests(unittest.TestCase):
	def setUp(self):
		self.sym_name = ''.join(random.choice(string.ascii_letters) for _ in range(10))
		self.sym_value = ''.join(random.choice(string.ascii_letters) for _ in range(10))

	def _type_resolver(self, name):
		if name == self.sym_name:
			return ast.DataType.STRING
		return ast.DataType.UNDEFINED

	def test_ast_expression_symbol(self):
		symbol = ast.SymbolExpression(engine.Context(), self.sym_name)
		self.assertIs(symbol.result_type, ast.DataType.UNDEFINED)
		self.assertEqual(symbol.name, self.sym_name)
		self.assertEqual(symbol.evaluate({self.sym_name: self.sym_value}), self.sym_value)

	def test_ast_expression_symbol_scope(self):
		symbol = ast.SymbolExpression(context, 'test', scope='built-in')
		expression = ast.GetAttributeExpression(context, symbol, 'one')
		value = expression.evaluate(None)
		self.assertIsInstance(value, float)
		self.assertEqual(value, 1.0)

	def test_ast_expression_symbol_scope_error(self):
		symbol = ast.SymbolExpression(context, 'fake-name', scope='fake-scope')
		try:
			symbol.evaluate(None)
		except errors.SymbolResolutionError as error:
			self.assertEqual(error.symbol_name, 'fake-name')
			self.assertEqual(error.symbol_scope, 'fake-scope')
		else:
			self.fail('SymbolResolutionError was not raised')

	def test_ast_expression_symbol_type(self):
		context = engine.Context(type_resolver=self._type_resolver)
		symbol = ast.SymbolExpression(context, self.sym_name)
		self.assertIs(symbol.result_type, ast.DataType.STRING)
		self.assertEqual(symbol.name, self.sym_name)
		self.assertEqual(symbol.evaluate({self.sym_name: self.sym_value}), self.sym_value)

	def test_ast_expression_symbol_type_errors(self):
		context = engine.Context(type_resolver=self._type_resolver)
		symbol = ast.SymbolExpression(context, self.sym_name)
		self.assertIs(symbol.result_type, ast.DataType.STRING)
		self.assertEqual(symbol.name, self.sym_name)
		with self.assertRaises(errors.SymbolTypeError):
			self.assertEqual(symbol.evaluate({self.sym_name: not self.sym_value}), self.sym_value)
		self.assertIsNone(symbol.evaluate({self.sym_name: None}))

class SymbolExpressionConversionTests(unittest.TestCase):
	def setUp(self):
		self.sym_name = ''.join(random.choice(string.ascii_letters) for _ in range(10))
		self.symbol = ast.SymbolExpression(context, self.sym_name)
		self.assertEqual(self.symbol.name, self.sym_name)

	def test_ast_expression_symbol_type_converts_date(self):
		result = self.symbol.evaluate({self.sym_name: datetime.date(2016, 10, 15)})
		self.assertIsInstance(result, datetime.datetime)
		self.assertEqual(result, datetime.datetime(2016, 10, 15, tzinfo=dateutil.tz.tzlocal()))

	def test_ast_expression_symbol_type_converts_int(self):
		result = self.symbol.evaluate({self.sym_name: 1})
		self.assertIsInstance(result, float)
		self.assertEqual(result, 1.0)

	def test_ast_expression_symbol_type_converts_range(self):
		result = self.symbol.evaluate({self.sym_name: range(3)})
		self.assertIsInstance(result, tuple)
		self.assertEqual(result, (0, 1, 2))

class TernaryExpressionTests(unittest.TestCase):
	left_value = ast.StringExpression(context, 'left')
	right_value = ast.StringExpression(context, 'right')
	def test_ast_expression_ternary(self):
		for value in trueish:
			ternary = ast.TernaryExpression(context, value, case_true=self.left_value, case_false=self.right_value)
			self.assertEqual(ternary.evaluate(None), self.left_value.value)
		for value in falseish:
			ternary = ast.TernaryExpression(context, value, case_true=self.left_value, case_false=self.right_value)
			self.assertEqual(ternary.evaluate(None), self.right_value.value)

class UnaryExpressionTests(unittest.TestCase):
	def test_ast_expression_unary_not(self):
		for value in trueish:
			unary = ast.UnaryExpression(context, 'not', value)
			self.assertFalse(unary.evaluate(None))
		for value in falseish:
			unary = ast.UnaryExpression(context, 'not', value)
			self.assertTrue(unary.evaluate(None))

	def test_ast_expression_unary_uminus(self):
		for value in trueish:
			if not isinstance(value, ast.FloatExpression):
				continue
			unary = ast.UnaryExpression(context, 'uminus', value)
			result = unary.evaluate(None)
			self.assertTrue(result)
			self.assertNotEqual(result, value.value)
		for value in falseish:
			if not isinstance(value, ast.FloatExpression):
				continue
			unary = ast.UnaryExpression(context, 'uminus', value)
			result = unary.evaluate(None)
			self.assertFalse(result)
			self.assertEqual(result, value.value)

	def test_ast_expresison_unary_minus_type_errors(self):
		for value in trueish + falseish:
			if isinstance(value, ast.FloatExpression):
				continue
			unary = ast.UnaryExpression(context, 'uminus', value)
			with self.assertRaises(errors.EvaluationError):
				unary.evaluate(None)

if __name__ == '__main__':
	unittest.main()
