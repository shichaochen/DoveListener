#!/usr/bin/env python3
"""
将 TensorFlow Lite 模型转换为 C 数组，供 Arduino 代码嵌入

使用方法：
python convert_model_to_c_array.py models/dove_detector.tflite esp32/model.h
"""

import sys
import argparse

def convert_tflite_to_c_array(tflite_path, output_path):
    """将 .tflite 文件转换为 C 数组"""
    with open(tflite_path, 'rb') as f:
        model_data = f.read()
    
    # 生成 C 数组
    array_name = "g_model"
    c_code = f"""// 自动生成的 TensorFlow Lite 模型数据
// 来源: {tflite_path}
// 模型大小: {len(model_data)} 字节

#ifndef MODEL_H
#define MODEL_H

#include "tensorflow/lite/schema/schema_generated.h"

alignas(8) const unsigned char {array_name}[] = {{
"""
    
    # 每行 16 个字节
    for i in range(0, len(model_data), 16):
        chunk = model_data[i:i+16]
        hex_values = ', '.join(f'0x{b:02x}' for b in chunk)
        c_code += f"  {hex_values},\n"
    
    c_code += f"""}};
const int {array_name}_len = {len(model_data)};

#endif  // MODEL_H
"""
    
    with open(output_path, 'w') as f:
        f.write(c_code)
    
    print(f"✓ 模型已转换为 C 数组: {output_path}")
    print(f"  模型大小: {len(model_data) / 1024:.2f} KB")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='将 TFLite 模型转换为 C 数组')
    parser.add_argument('tflite_path', type=str, help='TensorFlow Lite 模型路径')
    parser.add_argument('output_path', type=str, help='输出的 C 头文件路径')
    
    args = parser.parse_args()
    convert_tflite_to_c_array(args.tflite_path, args.output_path)

