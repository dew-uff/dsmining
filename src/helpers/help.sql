SELECT * FROM python_files where name like '%env%';

SELECT * FROM python_file_modules where python_file_id in (SELECT id FROM python_files where name like '%env%');
SELECT * FROM python_file_data_ios where python_file_id in (SELECT id FROM python_files where name like '%env%');
SELECT * FROM modules where python_file_id in (SELECT id FROM python_files where name like '%env%');
SELECT * FROM data_ios where python_file_id in (SELECT id FROM python_files where name like '%env%');


DELETE FROM python_file_modules WHERE python_file_id IN (SELECT id FROM python_files WHERE name LIKE '%env%');
DELETE FROM python_file_data_ios WHERE python_file_id IN (SELECT id FROM python_files WHERE name LIKE '%env%');
DELETE FROM modules WHERE python_file_id IN (SELECT id FROM python_files WHERE name LIKE '%env%');
DELETE FROM data_ios WHERE python_file_id IN (SELECT id FROM python_files WHERE name LIKE '%env%');

DELETE FROM python_files WHERE name LIKE '%env%';


ATTACH '/home/luam/Documentos/UFF/TCC/dsmining/dsmining/src/db/part0.sqlite' as part0;

INSERT INTO repositories SELECT * from part0.repositories;
INSERT INTO extractions  SELECT * from part0.extractions;
INSERT INTO commits      SELECT * from part0.commits;

INSERT INTO notebooks    SELECT * from part0.notebooks;
INSERT INTO python_files SELECT * from part0.python_files;
INSERT INTO requirement_files SELECT * from part0.requirement_files;

INSERT INTO cells      SELECT * from part0.cells;
INSERT INTO cell_modules      SELECT * from part0.cell_modules;
INSERT INTO cell_data_ios      SELECT * from part0.cell_data_ios;

INSERT INTO cell_markdown_features      SELECT * from part0.cell_markdown_features;
INSERT INTO python_file_modules      SELECT * from part0.python_file_modules;
INSERT INTO python_file_data_ios      SELECT * from part0.python_file_data_ios;

INSERT INTO modules      SELECT * from part0.modules;
INSERT INTO data_ios      SELECT * from part0.data_ios;
INSERT INTO notebook_markdowns      SELECT * from part0.notebook_markdowns;

SELECT * FROm repositories;

SELECT COUNT(*), *
FROM cell_data_ios
GROUP BY repository_id, notebook_id, cell_id, line, source
HAVING COUNT(*) > 1;




ALTER TABLE repositories ADD COLUMN part INTEGER;
UPDATE repositories set extraction_id = extraction_id + 100000000000 WHERE id in (SELECT id from part7.repositories);
UPDATE repositories set part = 6  WHERE extraction_id between 600000000000 and 700000000000 ;
ATTACH database '/home/luam/Documentos/UFF/TCC/dsmining/dsmining/src/db/part5.sqlite' as part5;
UPDATE repositories set part=5 WHERE id in (SELECT id from part5.repositories);



UPDATE repositories set extraction_id = extraction_id - 80000000000 + 800000000000 WHERE id in (SELECT id from part8.repositories);
UPDATE extractions set id = id - 80000000000 + 800000000000 WHERE id in (SELECT id from part8.extractions);




SELECT min(id), * FROM commits GROUP BY repository_id, hash;
BEGIN;
DELETE FROM commits where id not in (SELECT min(id) from commits group by repository_id, hash);
COMMIT;
