import streamlit as st
from PIL import Image, ImageOps

st.set_page_config(page_title="Image → Data", page_icon="🖼️", layout="wide")

RESAMPLE = Image.Resampling.LANCZOS


def daten(img):
    if hasattr(img, "get_flattened_data"):
        return list(img.get_flattened_data())
    return list(img.getdata())


def bild_laden(datei, size, stretch):
    img = Image.open(datei)
    img = ImageOps.exif_transpose(img).convert("RGBA")
    if stretch:
        return img.resize((size, size), RESAMPLE)
    img = ImageOps.contain(img, (size, size), RESAMPLE)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(img, ((size - img.width) // 2, (size - img.height) // 2))
    return canvas


def umwandeln(datei, size, max_colors, stretch):
    img = bild_laden(datei, size, stretch)
    pixels = daten(img)

    solide = [(r, g, b) for r, g, b, a in pixels if a >= 128]
    if not solide:
        return [[0] * size for _ in range(size)], {}
    mittel = tuple(sum(c[i] for c in solide) // len(solide) for i in range(3))

    rgb = Image.new("RGB", (size, size))
    rgb.putdata([(r, g, b) if a >= 128 else mittel for r, g, b, a in pixels])
    quant = rgb.quantize(colors=max_colors, method=Image.Quantize.MEDIANCUT)
    pal = quant.getpalette()
    indices = daten(quant)

    mapping = {}
    palette = {}
    data = []
    for (r, g, b, a), idx in zip(pixels, indices):
        if a < 128:
            data.append(0)
            continue
        if idx not in mapping:
            mapping[idx] = len(mapping) + 1
            palette[mapping[idx]] = (pal[idx * 3], pal[idx * 3 + 1], pal[idx * 3 + 2])
        data.append(mapping[idx])

    rows = [data[i * size:(i + 1) * size] for i in range(size)]
    return rows, palette


def als_js(rows, palette):
    zeilen = ["let [x, y, z] = thisPos;", "y += 10;", "", "const palette = {"]
    for nr, (r, g, b) in palette.items():
        zeilen.append(f"    {nr}: [{r}, {g}, {b}, 1],")
    zeilen.append("};")
    zeilen.append("")
    zeilen.append("let data = [")
    for row in rows:
        zeilen.append("    [" + ",".join(str(v) for v in row) + "],")
    zeilen.append("];")
    zeilen.append("")
    zeilen.append("drawImage(data, palette, x ,y ,z ,5);")
    return "\n".join(zeilen)


def vorschau(rows, palette, scale=10):
    size = len(rows)
    img = Image.new("RGB", (size, size), (30, 30, 30))  # transparent = dark gray
    px = img.load()
    for y, row in enumerate(rows):
        for x, v in enumerate(row):
            if v:
                px[x, y] = palette[v]
    return img.resize((size * scale, size * scale), Image.Resampling.NEAREST)


st.title("🖼️ Image → Data Array")
st.caption("Converts an image into a small pixel palette and a JS array.")

with st.sidebar:
    st.header("Settings")
    size = st.slider("Size (pixels per side)", 4, 40, 40)
    max_colors = st.slider("Max. colors", 2, 32, 10)
    stretch = st.checkbox("Stretch to square", value=False,
                          help="Off: aspect ratio is kept, the rest becomes transparent (0).")

datei = st.file_uploader("Upload image", type=["png", "jpg", "jpeg", "bmp", "gif", "webp"])

if datei is None:
    st.info("Upload an image to get started.")
    st.stop()

try:
    rows, palette = umwandeln(datei, size, max_colors, stretch)
except Exception as e:
    st.error(f"The image could not be processed: {e}")
    st.stop()

text = als_js(rows, palette)

col1, col2 = st.columns(2)
with col1:
    st.subheader("Original")
    st.image(datei, use_container_width=True)
with col2:
    st.subheader(f"Result ({size}×{size}, {len(palette)} colors)")
    st.image(vorschau(rows, palette, max(1, 400 // size)), use_container_width=True)

if palette:
    st.subheader("Palette")
    cols = st.columns(len(palette))
    for c, (nr, (r, g, b)) in zip(cols, palette.items()):
        hexfarbe = f"#{r:02x}{g:02x}{b:02x}"
        c.markdown(
            f"<div style='background:{hexfarbe};height:40px;border-radius:6px'></div>"
            f"<small>{nr}: {hexfarbe}</small>",
            unsafe_allow_html=True,
        )

st.subheader("Code")
st.code(text, language="javascript")  # has a copy button in the top right
st.download_button("Download as output.txt", text, file_name="output.txt")