



curl -X POST http://localhost:5000/bare_m_times
curl -X POST http://localhost:5000/dockers_times

curl -X POST http://localhost:5000/rss_bm

curl -X POST http://localhost:5000/rapl_bm

curl -X POST http://localhost:5000/doc_rss


curl -X POST http://localhost:5000/doc_rapl_bm


curl -X POST http://localhost:5000/run_script -H "Content-Type: application/json" -d '{
    "script_name": "times-new.py",
    "arguments": [0, 1, 2, 3],
    "location": "vpc"
}'


curl -X POST http://localhost:5000/run_profiling      -H "Content-Type: application/json"      -d '{"application_name": "2mm", "opt_levels": [2,3]}'



