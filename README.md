# brewlytics
This Github is for testing brewlytics Python script repositories


* [Model - Scikit-learn DecisonTreeClassifier - Ellipse Classifier](https://demo.brewlytics.com/app/#/build/4e6c1944-328a-47dc-b1cd-119b5101f61d)

This brewlytics model demonstrates how a Scikit-learn DecisionTree machine learning algorithm can be setup in a brewlytics environment using the new Python Script functionals using the Machine Learnine Runtime environment. This example uses a synthetic ellipse dataset that was randomly created for latitude, longitude, semi-major axis, and semi-minor axis. The ellipse eccentricity and area were calculated using Python in a sweperate brewlytics model. This DecisionTree features columns are user-provided inputs that include eccentricity and area. The target for this dataset was calculated by setting a semi-minor axis threshold value of equal to or less than 5.1 nautical miles as a "good" ellipse, and those with a semi-minor axis greater than 5.1 nautical miles as a "bad" ellipse. 
