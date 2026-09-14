from PIL import Image, ImageDraw

# TODO: potentially add named constructors? e.g. BrushStroke('topbar') -> [(1,1),(1,7)]
class BrushStroke():
    def __init__(self, path: list[tuple[int,int]], thickness: int = 6.0, weight: int | list[int] = 3):
        if type(weight) is list:
            if len(weight) != len(path):
                raise ValueError('A list of weights must be the same length as the path list')

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

        if not hasattr(_active_canvas, "margin"): raise AttributeError('canvas does not have attribute "margin"')
        if not hasattr(_active_canvas, "subdivision"): raise AttributeError('canvas does not have attribute "subdivision"')

        _canvas_area = tuple(x - _active_canvas.margin * 2 for x in _active_canvas.size)
        _canvas_fraction = tuple(x/_active_canvas.subdivision for x in _canvas_area)

        # repeat coords to reduce bezier smoothing; _weighting = level of smoothness
        _weighted_path = []
        for idx, coord in enumerate(self.path):
            if type(self.weight) is list:
                _weighted_path += [coord,] * self.weight[idx]
            else:
                _weighted_path += [coord,] * self.weight

        _scaled_path = []

        for x in _weighted_path:
            _pos = tuple((_active_canvas.margin + (x[n] * _canvas_fraction[n]) - (_canvas_fraction[n]/2)) for n in [0,1])
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

# TODO: classify, convert canvas generation and BrushStroke.draw() calls to a Glyph.draw() call. Add defs, pronunciation, etc. Also fromJSON constructor?
def DrawCharacter(strokes: list[BrushStroke]):
    """
    Constructs a PIL.Image from a list of brush strokes.

    :param strokes: A list of `BrushStroke`s. These define the 'cells' that the 'brush' passes through during a single line stroke.
    :type strokes: list[BrushStroke]

    """
    _active_canvas = Image.new(mode = "RGBA", size = (128,128), color = (255,255,255,255))
    _active_canvas.margin = 1
    _active_canvas.subdivision = 7

    for stroke in strokes:
        _active_canvas = stroke.draw(_active_canvas)

    return _active_canvas