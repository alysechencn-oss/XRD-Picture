"""Streamlit app for generating editable Python plotting scripts from XRD data."""

from __future__ import annotations

import io
from textwrap import dedent

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st


st.set_page_config(page_title="AutoXRD Coder", layout="wide", page_icon="🧪")
st.title("🧪 AutoXRD: 从数据到 Python 绘图代码")
st.markdown(
    "上传您的 XRD 数据，自动生成可编辑的 Matplotlib 绘图脚本。"
)


with st.sidebar:
    st.header("⚙️ 绘图参数")
    plot_color = st.color_picker("线条颜色", "#1f77b4")
    line_width = st.slider("线条宽度", 0.5, 4.0, 1.5, 0.1)
    fig_style = st.selectbox(
        "图表风格", ["default", "classic", "bmh", "seaborn-v0_8-white"]
    )

    st.subheader("坐标轴设置")
    xlabel = st.text_input("X轴标签", r"2$\theta$ (degree)")
    ylabel = st.text_input("Y轴标签", "Intensity (a.u.)")
    hide_top_right = st.checkbox("去除右/上边框 (Nature风格)", value=True)
    x_min = st.number_input("X轴最小值 (可选)", value=None, step=1.0, format="%f")
    x_max = st.number_input("X轴最大值 (可选)", value=None, step=1.0, format="%f")

    st.subheader("AI 指令（占位）")
    ai_hint = st.text_area(
        "描述希望的改动 (当前版本仅做记录)",
        help="未来可与 LLM 对接，根据指令自动修改代码",
    )


uploaded_file = st.file_uploader("上传数据文件 (.txt, .csv, .xy)", type=["txt", "csv", "xy"])


def _build_code_template(
    *,
    file_name: str,
    color: str,
    linewidth: float,
    style: str,
    x_label: str,
    y_label: str,
    drop_spines: bool,
    x_min_value: float | None,
    x_max_value: float | None,
) -> str:
    optional_xlim = ""
    if x_min_value is not None or x_max_value is not None:
        optional_xlim = f"\nax.set_xlim({x_min_value}, {x_max_value})"

    optional_spines = dedent(
        """
        # 去除上方和右方边框
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_linewidth(1.2)
        ax.spines['bottom'].set_linewidth(1.2)
        """
    )

    code = f"""import matplotlib.pyplot as plt
import pandas as pd

# 1. 设置全局风格
plt.style.use('{style}')
plt.rcParams['font.family'] = 'Arial'  # 科研常用字体
plt.rcParams['font.size'] = 12

# 2. 读取数据
# 注意：生成的脚本假设数据文件 '{file_name}' 与脚本在同一目录下
df = pd.read_csv('{file_name}', sep=None, engine='python', header=None)
x = df.iloc[:, 0]
y = df.iloc[:, 1]

# 3. 创建画布
fig, ax = plt.subplots(figsize=(6, 4.5), dpi=300)

# 4. 绘图
ax.plot(x, y, color='{color}', linewidth={linewidth}, label='{file_name}')

# 5. 细节调整
ax.set_xlabel(r'{x_label}', fontsize=14, fontweight='bold')
ax.set_ylabel(r'{y_label}', fontsize=14, fontweight='bold')
ax.tick_params(direction='in', length=6, width=1){optional_xlim}
{optional_spines if drop_spines else ''}

plt.legend(frameon=False)
plt.tight_layout()

# 6. 保存
output_name = '{file_name.rsplit('.', 1)[0]}_plot.png'
plt.savefig(output_name)
print(f"图片已保存为: {{output_name}}")
plt.show()
"""
    return code


def _render_preview(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(6, 4.5))
    plt.style.use(fig_style)
    ax.plot(df.iloc[:, 0], df.iloc[:, 1], color=plot_color, linewidth=line_width)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if x_min is not None or x_max is not None:
        ax.set_xlim(x_min, x_max)
    if hide_top_right:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_linewidth(1.2)
        ax.spines["bottom"].set_linewidth(1.2)
    st.pyplot(fig)
    plt.close(fig)


if uploaded_file is not None:
    try:
        buffer = io.BytesIO(uploaded_file.read())
        df_preview = pd.read_csv(buffer, sep=None, engine="python", header=None)
        df_preview = df_preview.iloc[:, :2]
        df_preview.columns = ["2Theta", "Intensity"]

        col1, col2 = st.columns([1, 2])
        with col1:
            st.write("### 📊 数据预览")
            st.dataframe(df_preview.head(5), height=180)
            st.write("### 🖼️ 效果预览")
            _render_preview(df_preview)

        with col2:
            st.write("### 🐍 生成的 Python 代码")
            code_template = _build_code_template(
                file_name=uploaded_file.name,
                color=plot_color,
                linewidth=line_width,
                style=fig_style,
                x_label=xlabel,
                y_label=ylabel,
                drop_spines=hide_top_right,
                x_min_value=x_min,
                x_max_value=x_max,
            )
            st.code(code_template, language="python")
            st.download_button(
                label="📥 下载 .py 脚本文件",
                data=code_template,
                file_name=f"plot_{uploaded_file.name.rsplit('.', 1)[0]}.py",
                mime="text/x-python",
            )

            if ai_hint:
                st.info(
                    "AI 指令已记录：当前版本不会自动改动代码，未来可将其传递给 LLM 服务。"
                )

            st.caption(
                "💡 下载脚本后，请将其与数据文件放在同一文件夹下运行。"
            )

    except Exception as exc:  # noqa: BLE001
        st.error(f"文件解析错误: {exc}")
else:
    st.info("请上传包含两列 2θ 与强度的 XRD 数据文件开始体验。")
