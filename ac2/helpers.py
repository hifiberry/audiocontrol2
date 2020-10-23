'''
Copyright (c) 2018 Modul 9/HiFiBerry

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''


def array_to_string(arr, do_not_flatten_strings=True):
    """
    Converts an array of objects to a comma separated string
    """
    res = ""

    if arr is None:
        return None
    
    if do_not_flatten_strings and isinstance(arr, str):
        return arr

    if hasattr(arr, '__iter__'):
        for part in arr:
            if part is not None:
                res = res + str(part) + ", "
        if len(res) > 1:
            return res[:-2]
        else:
            return ""
    else:
        return str(arr)


"""
A simple function that allows to map attributes to different keys

e.g. 

dst={}
map_attribute({"k1":"v1"},dst,{"k1":"n1"})
pritn(dst)
{"k1":"v1"}
"""
def map_attributes(src, dst, mapping, flatten_array=True):
    for key in src:
        if key in mapping:
            if flatten_array:
                dst[mapping[key]]=array_to_string(src[key])
            else:
                dst[mapping[key]]=src[key]
            