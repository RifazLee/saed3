ALTER TABLE hkl_reflections MODIFY reflection_status ENUM('Allowed','Forbidden','Centering-compatible','Requires SG verification') NOT NULL;

-- CIF source and atomic structure are stored per immutable material version.
ALTER TABLE material_versions
  ADD COLUMN cif_file_name VARCHAR(255) NULL,
  ADD COLUMN cif_text MEDIUMTEXT NULL,
  ADD COLUMN atomic_structure_json JSON NULL,
  ADD COLUMN scattering_model VARCHAR(180) NULL,
  ADD COLUMN scattering_reference VARCHAR(500) NULL,
  ADD COLUMN intensity_model VARCHAR(255) NULL;

ALTER TABLE hkl_reflections
  ADD COLUMN shkl_magnitude DOUBLE NULL,
  ADD COLUMN f_real DOUBLE NULL,
  ADD COLUMN f_imag DOUBLE NULL,
  ADD COLUMN f_magnitude DOUBLE NULL,
  ADD COLUMN f_intensity DOUBLE NULL,
  ADD COLUMN f_status ENUM('Allowed','Forbidden') NULL,
  ADD COLUMN final_status VARCHAR(80) NULL;
