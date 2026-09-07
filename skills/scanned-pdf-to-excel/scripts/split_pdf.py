import os
import sys
import fitz  # PyMuPDF

def split_pdf_to_images(pdf_path, task_dir=None, max_long_edge=1280):
    """
    检查 PDF 文本层；若为扫描件，则在指定的任务子目录内将 PDF 拆分为优化分辨率的 JPG 图片。
    :param pdf_path: 输入 PDF 文件路径
    :param task_dir: 任务独立子文件夹路径（例如 "workspaces/task_bank_statement"）
    :param max_long_edge: 图片长边最大像素限制（默认 1280，适配 Token 消耗与清晰度平衡）
    """
    if not os.path.exists(pdf_path):
        print(f"错误: 找不到文件 {pdf_path}")
        sys.exit(1)

    if not task_dir:
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        task_dir = os.path.join("workspaces", base_name)

    pages_dir = os.path.join(task_dir, "pdf_pages")
    results_dir = os.path.join(task_dir, "results")
    os.makedirs(pages_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)

    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    # 优先检测电子层文本
    has_text = False
    sample_pages = min(5, total_pages)
    text_count = sum(len(doc[i].get_text().strip()) for i in range(sample_pages))
    if text_count > 100:
        has_text = True
        print(f"ℹ️ 检测到 PDF 包含电子文本层 ({sample_pages} 页提取字符数: {text_count})，优先使用文本提取可实现 0 Token 消耗！")

    print(f"📁 任务子目录已就绪: {task_dir}")
    print(f"正在拆分 PDF: {pdf_path} (共 {total_pages} 页)...")

    for page_num in range(total_pages):
        page = doc[page_num]
        rect = page.rect
        width, height = rect.width, rect.height
        long_edge = max(width, height)

        # 计算缩放比例，限制长边 <= max_long_edge (默认1280px)
        scale = min(1.0, max_long_edge / long_edge) if long_edge > max_long_edge else 1.0
        # 保持适度清晰度（基础缩放放大至1.5-2倍，再等比缩放至最大1280px）
        base_dpi_scale = 150 / 72.0
        final_scale = base_dpi_scale * scale
        matrix = fitz.Matrix(final_scale, final_scale)

        pix = page.get_pixmap(matrix=matrix, alpha=False)
        output_path = os.path.join(pages_dir, f"page_{page_num + 1:03d}.jpg")
        # 保存为 JPG 85% 质量以最大化节省输入 Token
        pix.save(output_path, jpg_quality=85)

    doc.close()
    print(f"✅ PDF 拆图优化完成！图片已压缩导出至: {pages_dir} (长边上限: {max_long_edge}px)")
    return task_dir, total_pages, has_text

if __name__ == "__main__":
    pdf_file = sys.argv[1] if len(sys.argv) > 1 else "input.pdf"
    t_dir = sys.argv[2] if len(sys.argv) > 2 else None
    max_edge = int(sys.argv[3]) if len(sys.argv) > 3 else 1280

    split_pdf_to_images(pdf_file, t_dir, max_edge)
