import React from "react";
import {render} from "react-dom";
import MuiThemeProvider from "material-ui/styles/MuiThemeProvider";
import AppBar from "material-ui/AppBar";
import {HashRouter, Route, Switch} from "react-router-dom";
import AllComics from "./components/AllComics";
import ComicDetailPage from "./components/ComicDetailPage";
import VolumeBrowser from "./components/VolumeBrowser";

function App() {
    return <MuiThemeProvider>
        <AppBar
                title="Comic"
                iconClassNameRight="muidocs-icon-navigation-expand-more"
            />
    </MuiThemeProvider>
}

render(
    <HashRouter>
        <div>
            <App/>
            <Switch>
                <Route path="/comic/:comic_id/:volume_id" component={VolumeBrowser}/>
                <Route path="/comic/:comic_id" component={ComicDetailPage}/>
                <Route path="/" component={AllComics}/>
            </Switch>
        </div>
    </HashRouter>,
    document.getElementById('root')
);

{/*render(<App/>, document.getElementById('root'))*/
}


// export function onComicItemClick(comic_id) {
//     ReactDOM.render(
//         <MuiThemeProvider>
//             <ComicDetailPage comic_id={comic_id} onItemClick={onVolumeItemClick}/>
//         </MuiThemeProvider>,
//         document.getElementById('app_root')
//     );
// }
//
// export function onVolumeItemClick(comic_id, volume_id) {
//     ReactDOM.render(
//             <MuiThemeProvider>
//                 <VolumeBrowser comic_id={comic_id} volume_id={volume_id}/>
//             </MuiThemeProvider>,
//             document.getElementById('app_root')
//         );
// }
