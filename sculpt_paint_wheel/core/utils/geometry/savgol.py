import numpy as np

def savgol_coeffs(window, poly):
    if window % 2 == 0:
        raise ValueError("window must be odd")
    if poly >= window:
        raise ValueError("poly must be < window")

    half = window // 2
    x = np.arange(-half, half + 1, dtype=float)

    # Vandermonde
    A = np.vander(x, poly + 1, increasing=True)

    # Pseudoinversa
    ATA_inv = np.linalg.pinv(A.T @ A)
    coeffs = ATA_inv @ A.T

    # Coeficientes para el valor central (orden 0)
    return coeffs[0]

def savgol_filter_np(y, window=11, poly=3):
    coeffs = savgol_coeffs(window, poly)
    pad = window // 2
    y_pad = np.pad(y, pad, mode='edge')
    return np.convolve(y_pad, coeffs[::-1], mode='valid')

def savgol_filter_2d(points, window=11, poly=3):
    if points.ndim != 2 or points.shape[1] < 2:
        return points
        raise ValueError("points must be a 2D array with at least 2 columns")
    x = savgol_filter_np(points[:,0], window, poly)
    y = savgol_filter_np(points[:,1], window, poly)
    return np.column_stack((x, y))
