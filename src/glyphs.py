from PIL import Image, ImageDraw
from typing import Literal

GLYPH_MARGIN = 0.1

def add_constants(cls):
    HOR = [(0.0, 0.0), (1.0, 0.0)]
    VER = [(0.0, 0.0), (0.0, 1.0)]

    _offsets = [0.2, 0.4, 0.6, 0.8]

    for offset in _offsets:
        _hor_path = [(x, y + offset) for (x,y) in HOR]
        _ver_path = [(x + offset, y) for (x,y) in VER]

        _hor_constant_name = f"HOR_0{int(offset * 10)}"
        _ver_constant_name = f"VER_0{int(offset * 10)}"

        setattr(cls, _hor_constant_name, cls(path = _hor_path))
        setattr(cls, _ver_constant_name, cls(path = _ver_path))

    cls.TOP = cls(path = HOR)
    cls.HOR_CENTRE = cls(path=[(0.0, 0.5), (1.0, 0.5)])
    cls.BOTTOM = cls(path=[(0.0, 1.0), (1.0, 1.0)])

    cls.LEFT = cls(path = VER)
    cls.VER_CENTRE = cls(path=[(0.5, 0.0), (0.5, 1.0)])
    cls.RIGHT = cls(path=[(1.0, 0.0), (1.0, 1.0)])

    cls.LEG_LEFT = cls(path=[(0.1, 0.0), (0.1, 0.7), (0.0, 1.0)], weight = 2)

    cls.CIRCLE = cls(path=[(0.5, 0.0), (0.0, 0.0), (0.0, 0.5), (0.0, 1.0), (0.5, 1.0), (1.0, 1.0), (1.0, 0.5), (1.0, 0.0), (0.5, 0.0)], weight = 1)

    return cls

@add_constants 
class BrushStroke():
    def __init__(self, path: list[tuple[float, float]], thickness: float = 6.0, weight: int | list[int] = 4):
        if type(weight) is list:
            if len(weight) != len(path):
                raise ValueError('A list of weights must be the same length as the path list')

        if any(not 0.0 <= value <= 1.0 for point in path for value in point):
            raise ValueError('Brush stroke coordinates must be between 0.0 and 1.0')

        self.path = path
        self.thickness = thickness
        self.weight = weight

    def pascal_row(self, n):
        """
        Returns the nth row of Pascal's triangle to solve the generalized Bezier Curve formula
        """
        result = [1]
        x, numerator = 1, n
        for denominator in range(1, n//2+1):
            # print(numerator,denominator,x)
            x *= numerator
            x /= denominator
            result.append(x)
            numerator -= 1
        if n&1 == 0:
            # n is even
            result.extend(reversed(result[:-1]))
        else:
            result.extend(reversed(result))
        return result

    def make_bezier(self, xys: list[tuple]):
        # xys should be a sequence of 2-tuples (Bezier control points)
        n = len(xys)
        combinations = self.pascal_row(n-1)
        def bezier(ts):
            # This uses the generalized formula for bezier curves
            # http://en.wikipedia.org/wiki/B%C3%A9zier_curve#Generalization
            result = []
            for t in ts:
                tpowers = (t**i for i in range(n))
                upowers = reversed([(1-t)**i for i in range(n)])
                coefs = [c*a*b for c, a, b in zip(combinations, tpowers, upowers)]
                result.append(
                    tuple(sum([coef*p for coef, p in zip(coefs, ps)]) for ps in zip(*xys)))
            return result
        return bezier

    def draw(self, canvas: Image):
        _active_canvas = canvas

        _canvas_area = tuple(x * (1 - GLYPH_MARGIN * 2) for x in _active_canvas.size)
        _canvas_margin = tuple(x * GLYPH_MARGIN for x in _active_canvas.size)

        # repeat coords to reduce bezier smoothing; _weighting = level of smoothness
        _weighted_path = []
        for idx, coord in enumerate(self.path):
            if type(self.weight) is list:
                _weighted_path += [coord,] * self.weight[idx]
            else:
                _weighted_path += [coord,] * self.weight

        _scaled_path = []

        for x in _weighted_path:
            _pos = tuple(_canvas_margin[n] + x[n] * _canvas_area[n] for n in [0, 1])
            _scaled_path.append(_pos)

        _draw = ImageDraw.Draw(_active_canvas)

        #generate n points along the bezier curve
        n_points = max(max(_active_canvas.size), 64)
        _bezier_points = self.make_bezier(_scaled_path)([t/n_points for t in range(n_points + 1)])

        for i, centre in enumerate(_bezier_points):
            _cur_thickness = (self.thickness - 1) * (len(_bezier_points) - i)/(len(_bezier_points)) + 1

            _draw.ellipse((centre[0] - _cur_thickness,
                        centre[1] - _cur_thickness,
                        centre[0] + _cur_thickness,
                        centre[1] + _cur_thickness),
                        fill=(0,0,0,255))
        return _active_canvas

class LangParticle():
    PARTICLE_TYPES = Literal["noun", "verb", "adjective", "adverb", "pronoun", "preposition", "conjunction", "number"]

    def __init__(self, particle_type: PARTICLE_TYPES, definition: str | int, strokes: BrushStroke | list[BrushStroke]):
        if any((particle_type == "number" and type(definition) is not int, particle_type != "number" and type(definition) is int)):
            raise ValueError("LangParticle `particle_type` and `definition` are incompatible!")

        self.glyph = self._generate_character(strokes)
        self.particle_type = particle_type
        self.definition = definition

    def _generate_character(self, strokes: list[BrushStroke]):
        """
        Constructs a PIL.Image from a list of brush strokes.

        :param strokes: A list of `BrushStroke`s. These define the 'cells' that the 'brush' passes through during a single line stroke.
        :type strokes: list[BrushStroke]

        """
        _active_canvas = Image.new(mode = "RGBA", size = (128,128), color = (255,255,255,255))

        if type(strokes) is list:
            for stroke in strokes:
                _active_canvas = stroke.draw(_active_canvas)
        else:
            _active_canvas = strokes.draw(_active_canvas)

        return _active_canvas