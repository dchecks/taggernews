## Tagger News

Currently this is still a work in progress. I haven't had this working completely, the last step is to get the articles tagging.

The server setup is now using mysql, a simple schema creation script can be found in the 'creates' file in the root directory.
If you want you can still use sqlite, just change the connection string in the settings.py file.

Importing now works, but is slow due to a python bug with OSX.
This prevents multiprocess parsing of the supervised_topics list which is needed for initial model building.
If you're running it on a proper nix try setting
```
THREAD_COUNT = 5
```
Or higher in refresh_top_articles.py (just don't abuse the hn api too much)

### Setup
##### Setup the environment
```
git clone http://github.com/danrobinson/taggernews.git
cd taggernews
mkvirtualenv taggernews
ln -s ~/.virtualenvs/taggernews/bin/activate ./activate
echo export SECRET_KEY="PICK A SECRET KEY" >> /location/of/your/.virtualenvs/taggernews/bin/activate
echo export DEBUG=True >> /location/of/your/.virtualenvs/taggernews/bin/activate
```
For some reason a 500 will be thrown on the admin page if you don't enable debug 

##### Dependencies
```
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
```

##### Start the server
```
python manage.py runserver
open http://localhost:8000
```
You should now see a tagger news clone start up with no data.

For the admin interface:
```
open http://localhost:8000/admin
```
###Data Gathering and Analysis

##### Importing
To import data run the commands:
```
python manage.py refresh_top_articles
```
This will start the parser which will continously run getting new articles and saving them to the db.
Currently this doesn't set the front page rank (due to meee! :P).

##### Create a model
Now to create an LDA model (Latent Dirichlet Allocation)
In analyze_hn run:
```
python tagger/model_topics.py
```
This will provide you with a dictionary and gensim files.


##### Prediction
Plug these into the predictor 
```
python tagger/predict_topics.py
```
The predictor will need to load in the training data on the first run. 
This is about 15k requests and so will take a lon time. Perhaps pre-run this step. 

##### Tagging
Using this training set you can now put the machine to work
```
python manage.py tag_articles
```

Things should be running now but I haven't got to this stage...