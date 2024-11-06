import os
import glob
import scipy.io
import numpy as np
from PIL import Image
import pandas as pd

def load_mat_files(directory):
    """Load all .mat files from the given directory."""
    mat_files = glob.glob(os.path.join(directory, '*.mat'))
    data = []
    for mat_file in mat_files:
        mat_data = scipy.io.loadmat(mat_file)
        data.append((mat_file, mat_data))
    return data

def generate_thumbnail(image_array, thumbnail_size=(128, 128)):
    """Generate a thumbnail from the image array."""
    image = Image.fromarray(image_array)
    image.thumbnail(thumbnail_size)
    return image

def save_thumbnail(image, save_path):
    """Save the thumbnail image to the specified path."""
    image.save(save_path)

def extract_metadata(mat_data):
    """Extract metadata from mat_data."""
    # This function should be customized based on the structure of your .mat files
    metadata = {
        'example_field': mat_data.get('example_field', 'N/A')  # Replace 'example_field' with actual field names
    }
    return metadata

def process_mat_files(input_directory, output_directory, csv_path):
    """Process all .mat files, generate thumbnails, and save metadata to CSV."""
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    mat_files_data = load_mat_files(input_directory)
    records = []

    for mat_file, mat_data in mat_files_data:
        # Extract image data from .mat file
        image_array = np.array(mat_data['image'])  # Replace 'image' with the actual image field name in your .mat files
        
        # Generate thumbnail
        thumbnail = generate_thumbnail(image_array)
        
        # Create save path for the thumbnail
        thumbnail_filename = os.path.splitext(os.path.basename(mat_file))[0] + '_thumbnail.png'
        thumbnail_save_path = os.path.join(output_directory, thumbnail_filename)
        
        # Save thumbnail
        save_thumbnail(thumbnail, thumbnail_save_path)
        
        # Extract metadata
        metadata = extract_metadata(mat_data)
        
        # Append record to list
        record = {
            'mat_file': mat_file,
            'thumbnail_path': thumbnail_save_path,
            **metadata
        }
        records.append(record)

    # Save all records to a CSV file
    df = pd.DataFrame(records)
    df.to_csv(csv_path, index=False)

if __name__ == '__main__':
    input_directory = rf'D:\lilith'  # Replace with your input directory
    output_directory = rf'E:\Yi\yi-editor-agent\data'  # Replace with your output directory
    csv_path = rf'E:\Yi\yi-editor-agent\output\metadata.csv'  # Replace with the path to save the CSV file

    process_mat_files(input_directory, output_directory, csv_path)
