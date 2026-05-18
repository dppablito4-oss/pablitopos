import zipfile
import os
import datetime

def create_code_backup():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    source_dir = r"e:\OneDrive\VISUAL STUDIO BOLETAS POS"
    backup_dir = os.path.join(source_dir, "backups")
    
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    backup_filename = f"code_backup_{timestamp}.zip"
    backup_path = os.path.join(backup_dir, backup_filename)
    
    print(f"Creating backup of {source_dir} to {backup_path}...")
    
    try:
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_dir):
                # Exclude the backups directory itself to prevent recursion
                if "backups" in dirs:
                    dirs.remove("backups")
                if "__pycache__" in dirs:
                    dirs.remove("__pycache__")
                if ".git" in dirs:
                    dirs.remove(".git")
                if ".gemini" in dirs:
                    dirs.remove(".gemini")
                    
                for file in files:
                    # Skip the backup file itself if it's being created (though it's in excluded dir)
                    if file == backup_filename:
                        continue
                        
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname)
                    
        print(f"Backup created successfully: {backup_path}")
        
    except Exception as e:
        print(f"Error creating backup: {e}")
        # Try to delete partial file
        if os.path.exists(backup_path):
            try:
                os.remove(backup_path)
            except:
                pass

if __name__ == "__main__":
    create_code_backup()
