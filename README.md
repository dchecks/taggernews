## Tagger News

Currently the server setup will work but importing and analysis does not.
I'm working on getting it going.


Setup the environment
```
git clone http://github.com/danrobinson/taggernews.git
cd taggernews
mkvirtualenv taggernews
ln -s ~/.virtualenvs/taggernews/bin/activate ./activate
echo export SECRET_KEY="PICK A SECRET KEY" >> /location/of/your/.virtualenvs/taggernews/bin/activate
echo export DEBUG=True >> /location/of/your/.virtualenvs/taggernews/bin/activate
```
For some reason a 500 will be thrown on the admin page if you don't enable debug 

Dependencies
```
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
```

Start the server
```
python manage.py runserver
open http://localhost:8000
```
You should now see a tagger news clone start up with no data.

For the admin interface:
```
open http://localhost:8000/admin
```
**Data Gathering and Analysis**

To import data run the commands:
```
python manage.py refresh_top_articles
```
This will start the parser which will continously run getting new articles and saving them to the db.

Now to create an LDA model (Latent Dirichlet Allocation)
In analyze_hn run:
```
python model_topics.py
```

This will provide you with a dictionary and gensim files.

Plug these into the predictor
```
python predict_topics
```


Using this training set you can now put the machine to work
```
python manage.py tag_articles
```