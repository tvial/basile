# Copyright (c) 2024 Thomas VIAL

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from unittest import TestCase
from dataclasses import dataclass
from typing import List

from expyriment import *


@dataclass
class Level2:
    field1: str


@dataclass
class Level1:
    field1: int
    field2: List[int]
    field3: Level2


class TestBinder(TestCase):
    def test_no_binding(self):
        template = Level1(
            field1=1,
            field2=[2, 3, 4],
            field3=Level2(field1='abc')
        )

        realizations = list(realize_template(template))
        self.assertListEqual([TemplateRealization({}, template)], realizations)

    def test_binding_at_level1(self):
        template = Level1(
            field1=1,
            field2=Either([2, 3, 4], [4, 5, 6]),
            field3=Level2(field1='abc')
        )

        expected = [
            TemplateRealization(
                {'field2': [2, 3, 4]},
                Level1(
                    field1=1,
                    field2=[2, 3, 4],
                    field3=Level2(field1='abc')
                )
            ),
            TemplateRealization(
                {'field2': [4, 5, 6]},
                Level1(
                    field1=1,
                    field2=[4, 5, 6],
                    field3=Level2(field1='abc')
                )
            ),
        ]
        realizations = list(realize_template(template))
        self.assertListEqual(expected, realizations)

    def test_binding_at_level2(self):
        template = Level1(
            field1=1,
            field2=[2, 3, 4],
            field3=Level2(field1=Either('abc', 'def'))
        )

        expected = [
            TemplateRealization(
                {'field3.field1': 'abc'},
                Level1(
                    field1=1,
                    field2=[2, 3, 4],
                    field3=Level2(field1='abc')
                )
            ),
            TemplateRealization(
                {'field3.field1': 'def'},
                Level1(
                    field1=1,
                    field2=[2, 3, 4],
                    field3=Level2(field1='def')
                )
            ),
        ]
        realizations = list(realize_template(template))
        self.assertListEqual(expected, realizations)

    def test_binding_at_both_levels(self):
        template = Level1(
            field1=1,
            field2=Either([2, 3, 4], [4, 5, 6]),
            field3=Level2(field1=Either('abc', 'def', 'ghi'))
        )

        expected = [
            TemplateRealization(
                {'field2': [2, 3, 4], 'field3.field1': 'abc'},
                Level1(
                    field1=1,
                    field2=[2, 3, 4],
                    field3=Level2(field1='abc')
                )
            ),
            TemplateRealization(
                {'field2': [2, 3, 4], 'field3.field1': 'def'},
                Level1(
                    field1=1,
                    field2=[2, 3, 4],
                    field3=Level2(field1='def')
                )
            ),
            TemplateRealization(
                {'field2': [2, 3, 4], 'field3.field1': 'ghi'},
                Level1(
                    field1=1,
                    field2=[2, 3, 4],
                    field3=Level2(field1='ghi')
                )
            ),
            TemplateRealization(
                {'field2': [4, 5, 6], 'field3.field1': 'abc'},
                Level1(
                    field1=1,
                    field2=[4, 5, 6],
                    field3=Level2(field1='abc')
                )
            ),
            TemplateRealization(
                {'field2': [4, 5, 6], 'field3.field1': 'def'},
                Level1(
                    field1=1,
                    field2=[4, 5, 6],
                    field3=Level2(field1='def')
                )
            ),
            TemplateRealization(
                {'field2': [4, 5, 6], 'field3.field1': 'ghi'},
                Level1(
                    field1=1,
                    field2=[4, 5, 6],
                    field3=Level2(field1='ghi')
                )
            ),
        ]
        realizations = list(realize_template(template))
        self.assertListEqual(expected, realizations)

    def test_binding_from_list(self):
        template = Level1(
            field1=1,
            field2=[1, Either(11, 12), Either(21, 22, 23)],
            field3=Level2(field1='abc')
        )

        sort_by_field2 = lambda tr: tr.realization.field2

        expected = sorted(
            [
                TemplateRealization(
                    {'field2.1': 11, 'field2.2': 21},
                    Level1(
                        field1=1,
                        field2=[1, 11, 21],
                        field3=Level2(field1='abc')
                    )
                ),
                TemplateRealization(
                    {'field2.1': 11, 'field2.2': 22},
                    Level1(
                        field1=1,
                        field2=[1, 11, 22],
                        field3=Level2(field1='abc')
                    )
                ),
                TemplateRealization(
                    {'field2.1': 11, 'field2.2': 23},
                    Level1(
                        field1=1,
                        field2=[1, 11, 23],
                        field3=Level2(field1='abc')
                    )
                ),
                TemplateRealization(
                    {'field2.1': 12, 'field2.2': 21},
                    Level1(
                        field1=1,
                        field2=[1, 12, 21],
                        field3=Level2(field1='abc')
                    )
                ),
                TemplateRealization(
                    {'field2.1': 12, 'field2.2': 22},
                    Level1(
                        field1=1,
                        field2=[1, 12, 22],
                        field3=Level2(field1='abc')
                    )
                ),
                TemplateRealization(
                    {'field2.1': 12, 'field2.2': 23},
                    Level1(
                        field1=1,
                        field2=[1, 12, 23],
                        field3=Level2(field1='abc')
                    )
                )
            ],
            key=sort_by_field2
        )

        realizations = sorted(realize_template(template), key=sort_by_field2)
        self.assertListEqual(expected, realizations)

    def test_binding_from_tuple(self):
        template = Level1(
            field1=1,
            field2=(1, Either(11, 12), Either(21, 22, 23)),
            field3=Level2(field1='abc')
        )

        sort_by_field2 = lambda tr: tr.realization.field2

        expected = sorted(
            [
                TemplateRealization(
                    {'field2.1': 11, 'field2.2': 21},
                    Level1(
                        field1=1,
                        field2=(1, 11, 21),
                        field3=Level2(field1='abc')
                    )
                ),
                TemplateRealization(
                    {'field2.1': 11, 'field2.2': 22},
                    Level1(
                        field1=1,
                        field2=(1, 11, 22),
                        field3=Level2(field1='abc')
                    )
                ),
                TemplateRealization(
                    {'field2.1': 11, 'field2.2': 23},
                    Level1(
                        field1=1,
                        field2=(1, 11, 23),
                        field3=Level2(field1='abc')
                    )
                ),
                TemplateRealization(
                    {'field2.1': 12, 'field2.2': 21},
                    Level1(
                        field1=1,
                        field2=(1, 12, 21),
                        field3=Level2(field1='abc')
                    )
                ),
                TemplateRealization(
                    {'field2.1': 12, 'field2.2': 22},
                    Level1(
                        field1=1,
                        field2=(1, 12, 22),
                        field3=Level2(field1='abc')
                    )
                ),
                TemplateRealization(
                    {'field2.1': 12, 'field2.2': 23},
                    Level1(
                        field1=1,
                        field2=(1, 12, 23),
                        field3=Level2(field1='abc')
                    )
                )
            ],
            key=sort_by_field2
        )

        realizations = sorted(realize_template(template), key=sort_by_field2)
        self.assertListEqual(expected, realizations)

    def test_binding_from_dict(self):
        template = Level1(
            field1=1,
            field2={'a': 1, 'b': Either(11, 12), 'c': Either(21, 22, 23)},
            field3=Level2(field1='abc')
        )

        sort_by_field2 = lambda tr: (tr.realization.field2['b'], tr.realization.field2['c'])

        expected = sorted(
            [
                TemplateRealization(
                    {'field2.b': 11, 'field2.c': 21},
                    Level1(
                        field1=1,
                        field2={'a': 1, 'b': 11, 'c': 21},
                        field3=Level2(field1='abc')
                    )
                ),
                TemplateRealization(
                    {'field2.b': 11, 'field2.c': 22},
                    Level1(
                        field1=1,
                        field2={'a': 1, 'b': 11, 'c': 22},
                        field3=Level2(field1='abc')
                    )
                ),
                TemplateRealization(
                    {'field2.b': 11, 'field2.c': 23},
                    Level1(
                        field1=1,
                        field2={'a': 1, 'b': 11, 'c': 23},
                        field3=Level2(field1='abc')
                    )
                ),
                TemplateRealization(
                    {'field2.b': 12, 'field2.c': 21},
                    Level1(
                        field1=1,
                        field2={'a': 1, 'b': 12, 'c': 21},
                        field3=Level2(field1='abc')
                    )
                ),
                TemplateRealization(
                    {'field2.b': 12, 'field2.c': 22},
                    Level1(
                        field1=1,
                        field2={'a': 1, 'b': 12, 'c': 22},
                        field3=Level2(field1='abc')
                    )
                ),
                TemplateRealization(
                    {'field2.b': 12, 'field2.c': 23},
                    Level1(
                        field1=1,
                        field2={'a': 1, 'b': 12, 'c': 23},
                        field3=Level2(field1='abc')
                    )
                ),
            ],
            key=sort_by_field2
        )

        realizations = sorted(realize_template(template), key=sort_by_field2)
        self.assertListEqual(expected, realizations)

    def test_count_realizations(self):
        template = Level1(
            field1=Either(1, 2, 3),
            field2={'a': 1, 'b': Either(11, 12), 'c': Either(21, 22, 23)},
            field3=Level2(field1=Either('abc', 'def', 'ghi', 'jkl'))
        )

        self.assertEqual(3*1*2*3*4, count_realizations(template))