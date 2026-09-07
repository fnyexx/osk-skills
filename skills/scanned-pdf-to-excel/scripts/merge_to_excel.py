import os
import sys
import json
import glob
import pandas as pd

def check_missing_pages(total_pages, json_dir="results"):
    """
    自检 missing 页码并输出列表
    """
    existing_files = set(os.path.basename(f) for f in glob.glob(os.path.join(json_dir, "*.json")))
    missing_pages = []
    for i in range(1, total_pages + 1):
        filename = f"page_{i:03d}.json"
        if filename not in existing_files:
            missing_pages.append(i)
    return missing_pages

def merge_json_results_to_excel(json_dir="results", output_excel="output.xlsx", total_pages=None):
    """
    读取指定目录下所有的表格识别结果 JSON 文件，检查完备性，合并组装并导出为 Excel。
    :param json_dir: 存放多页 JSON 结果的目录
    :param output_excel: 输出 Excel 文件路径
    :param total_pages: 预期总页数（传入时自动触发缺页自检）
    """
    if not os.path.exists(json_dir):
        print(f"错误: 结果目录 {json_dir} 不存在！")
        sys.exit(1)

    # 如果指定了总页数，先检查缺页
    if total_pages:
        missing = check_missing_pages(int(total_pages), json_dir)
        if missing:
            print(f"⚠️ [告警] 仍有 {len(missing)} 页未能识别成功: 页码 {missing}")
            print("请针对缺失页码补发识别任务后再进行最终组装！")

    json_files = sorted([f for f in os.listdir(json_dir) if f.endswith(".json")])
    if not json_files:
        print(f"提示: 在 {json_dir} 中未找到 JSON 文件！")
        return

    all_dfs = []
    print(f"正在扫描并读取 JSON 提取文件 (共 {len(json_files)} 个)...")

    for json_file in json_files:
        file_path = os.path.join(json_dir, json_file)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            tables = data.get("tables", [])
            for table in tables:
                headers = table.get("headers", [])
                rows = table.get("rows", [])

                if headers and rows:
                    df = pd.DataFrame(rows, columns=headers)
                    all_dfs.append(df)
                elif rows:
                    df = pd.DataFrame(rows)
                    all_dfs.append(df)
        except Exception as e:
            print(f"解析 {json_file} 失败: {str(e)}")

    if not all_dfs:
        print("未获取到可合并的表格数据。")
        return

    # 合并表格并写入 Excel
    try:
        combined_df = pd.concat(all_dfs, ignore_index=True)
        with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
            combined_df.to_excel(writer, sheet_name="合并表格数据", index=False)
        print(f"✅ 数据合并完毕！共组装 {len(combined_df)} 行交易记录，已生成 Excel 文件: {output_excel}")
    except Exception as e:
        print(f"❌ 生成 Excel 失败: {str(e)}")

if __name__ == "__main__":
    in_dir = sys.argv[1] if len(sys.argv) > 1 else "results"
    out_excel = sys.argv[2] if len(sys.argv) > 2 else "output.xlsx"
    t_pages = sys.argv[3] if len(sys.argv) > 3 else None

    merge_json_results_to_excel(in_dir, out_excel, t_pages)
