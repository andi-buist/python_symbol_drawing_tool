from PIL import Image, ImageDraw
import drawsvg as draw
import shapely.geometry as Geom
import numpy as np

def make_bezier(xys: list[tuple]):
    # xys should be a sequence of 2-tuples (Bezier control points)
    n = len(xys)
    combinations = pascal_row(n-1)
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

def pascal_row(n, memo={}):
    # This returns the nth row of Pascal's Triangle
    if n in memo:
        return memo[n]
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
    memo[n] = result
    return result

def DrawStroke(canvas: Image, strokepath: list[tuple[int,int]], thickness: float = 6.0):
    _active_canvas = canvas

    if not hasattr(_active_canvas, "margin"): raise AttributeError('canvas does not have attribute "margin"')
    if not hasattr(_active_canvas, "subdivision"): raise AttributeError('canvas does not have attribute "subdivision"')

    _canvas_area = tuple(x - canvas.margin * 2 for x in canvas.size)
    _canvas_fraction = tuple(x/canvas.subdivision for x in _canvas_area)

    # repeat coords to reduce bezier smoothing; _weighting = level of smoothness
    _weighting = 4
    _weighted_strokepath = []
    for coord in strokepath:
        _weighted_strokepath += [coord,] * _weighting

    _scaled_strokepath = []

    for i, x in enumerate(_weighted_strokepath):
        _pos = tuple((canvas.margin + (x[n] * _canvas_fraction[n]) - (_canvas_fraction[n]/2)) for n in [0,1])
        _scaled_strokepath.append(_pos)

    _draw = ImageDraw.Draw(_active_canvas)

    #generate n points along the bezier curve
    n_points = max(max(canvas.size), 64)
    _bezier_points = make_bezier(_scaled_strokepath)([t/n_points for t in range(n_points + 1)])

    for i, centre in enumerate(_bezier_points):
        _cur_thickness = (thickness - 1) * (len(_bezier_points) - i)/(len(_bezier_points)) + 1

        _draw.ellipse((centre[0] - _cur_thickness,
                       centre[1] - _cur_thickness,
                       centre[0] + _cur_thickness,
                       centre[1] + _cur_thickness),
                       fill=(0,0,0,255))
    return _active_canvas

def DrawCharacter(strokes: list[list[tuple[int,int]]],
                  thickness: float | list[float] = 6.0,
                  margin: int = 1,
                  subdivision: int = 7,
                  mode: str = "RGBA", size: tuple[int,int] = (128,128), color: tuple[int,int,int,int] = (255,255,255,255)):
    """
    Constructs a PIL.Image from a list of brush strokes.

    :param strokes: A list of lists of length-2 tuples. These define the 'cells' that the 'brush' passes through during a single line stroke.
    :type strokes: list[list[tuple[int,int]]]

    """
    if type(thickness) is list:
        if len(thickness) > 1 and len(thickness) != len(strokes):
            raise ValueError('strokes and thickness must be the same length!')

    _active_canvas = Image.new(mode = mode,
                                size = size,
                                color = color)
    _active_canvas.margin = margin
    _active_canvas.subdivision = subdivision

    for idx, stroke in enumerate(strokes):
        if type(thickness) is list:
            _cur_thickness = thickness[idx]
        else:
            _cur_thickness = thickness
        _active_canvas = DrawStroke(_active_canvas, stroke, _cur_thickness)

    return _active_canvas