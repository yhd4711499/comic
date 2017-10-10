import React from "react";
import {render} from "react-dom";
import {HashRouter, Route, Switch} from "react-router-dom";
import App from "./components/App";
import AllComics from "./components/AllComics";
import ComicDetailPage from "./components/ComicDetailPage";
import VolumeBrowser from "./components/VolumeBrowser";

render(
    <HashRouter>
        <App>
            <Switch>
                <Route path="/comic/:comic_id/:volume_id" component={VolumeBrowser}/>
                <Route path="/comic/:comic_id" component={ComicDetailPage}/>
                <Route path="/" component={AllComics}/>
            </Switch>
        </App>
    </HashRouter>,
    document.getElementById('root')
);